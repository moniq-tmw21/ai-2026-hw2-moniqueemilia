import argparse
import json
import os
from pathlib import Path

import jsonschema
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

CHAT_SCRIPT_PATH = DATA_DIR / "chat_script.json"
SCHEMA_PATH = DATA_DIR / "memory_state.schema.json"
POLICY_PATH = DATA_DIR / "policy.json"
RECORDS_PATH = DATA_DIR / "records.json"

MODEL = "gpt-5.6-luna"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def create_client():
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to the .env file."
        )

    return OpenAI(api_key=api_key)


def get_encoder():
    try:
        return tiktoken.encoding_for_model(MODEL)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(messages, encoder):
    text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in messages
    )
    return len(encoder.encode(text))


def build_system_message(policy, records):
    return f"""
You are a grant office assistant.

Answer the applicant using the official policy and records below.

Important rules:
- Use the official record as the source of truth.
- Do not accept an applicant's claim as proof when it conflicts with the record.
- Remember relevant information from the conversation.
- Do not invent information.
- Answer clearly and briefly.

Official policy:
{json.dumps(policy, ensure_ascii=False, indent=2)}

Official applicant records:
{json.dumps(records, ensure_ascii=False, indent=2)}
""".strip()


def build_messages(system_message, history):
    return [
        {
            "role": "system",
            "content": system_message,
        },
        *history,
    ]


def build_compressed_messages(
    system_message,
    memory,
    history_after_compression,
):
    return [
        {
            "role": "system",
            "content": system_message,
        },
        {
            "role": "system",
            "content": (
                "Structured memory from the earlier conversation:\n"
                + json.dumps(
                    memory,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            ),
        },
        *history_after_compression,
    ]


def call_assistant(client, messages):
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    return response.choices[0].message.content.strip()


def compress_conversation(client, history, schema):
    conversation_text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in history
    )

    prompt = f"""
Compress the conversation into one structured memory object.

Rules:
- Follow the supplied JSON schema exactly.
- Do not invent information.
- applicant_id is null if it was never established.
- facts contain facts stated or established in the conversation.
- decisions contain decisions established in the conversation.
- constraints contain conditions about when or how something can happen.
- open_questions contain applicant questions that remain unanswered.
- Arrays must always be present, even when empty.
- Do not add fields.
- Preserve information that may be needed later.

JSON schema:
{json.dumps(schema, ensure_ascii=False, indent=2)}

Conversation:
{conversation_text}
""".strip()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You compress a conversation into validated "
                    "structured JSON memory."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    memory = json.loads(content)

    jsonschema.validate(
        instance=memory,
        schema=schema,
    )

    return memory


def check_probe(answer, expected_strings):
    answer_lower = answer.lower()

    return any(
        expected.lower() in answer_lower
        for expected in expected_strings
    )


def run_uncompressed(
    chat_script,
    client,
    encoder,
    system_message,
):
    conversation = chat_script["conversation"]
    probes = chat_script["probes"]

    history = []
    token_counts = []

    print("\n" + "=" * 70)
    print("RUN A - UNCOMPRESSED")
    print("=" * 70)

    call_number = 0

    for turn in conversation:
        if turn == "<compress>":
            continue

        history.append(
            {
                "role": "user",
                "content": turn,
            }
        )

        call_number += 1

        messages = build_messages(
            system_message,
            history,
        )

        token_count = count_tokens(
            messages,
            encoder,
        )

        token_counts.append(token_count)

        print(
            f"Call {call_number}: "
            f"{token_count} tokens"
        )

        try:
            answer = call_assistant(
                client,
                messages,
            )

            history.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

            print(f"  Assistant: {answer}")

        except Exception as error:
            print(f"  API call failed: {error}")

    probe_results = []

    print("\nRun A probes:")

    for probe in probes:
        probe_messages = build_messages(
            system_message,
            history,
        )

        probe_messages.append(
            {
                "role": "user",
                "content": probe["question"],
            }
        )

        try:
            answer = call_assistant(
                client,
                probe_messages,
            )

            retrieved = check_probe(
                answer,
                probe["expect_contains"],
            )

            status = (
                "retrieved"
                if retrieved
                else "lost"
            )

            print(f"{probe['id']}: {status}")
            print(f"  Answer: {answer}")

            probe_results.append(
                {
                    "id": probe["id"],
                    "retrieved": retrieved,
                    "answer": answer,
                }
            )

        except Exception as error:
            print(
                f"{probe['id']}: could not run"
            )
            print(f"  Reason: {error}")

            probe_results.append(
                {
                    "id": probe["id"],
                    "retrieved": None,
                    "answer": None,
                }
            )

    return {
        "token_counts": token_counts,
        "peak": max(token_counts) if token_counts else 0,
        "total": sum(token_counts),
        "probes": probe_results,
    }


def run_compressed(
    chat_script,
    schema,
    client,
    encoder,
    system_message,
):
    conversation = chat_script["conversation"]
    probes = chat_script["probes"]

    history = []
    history_after_compression = []

    memory = None
    compression_succeeded = False

    token_counts = []

    print("\n" + "=" * 70)
    print("RUN B - COMPRESSED")
    print("=" * 70)

    call_number = 0

    for turn in conversation:
        if turn == "<compress>":
            print("\nCompression command reached.")

            try:
                new_memory = compress_conversation(
                    client,
                    history,
                    schema,
                )

                memory = new_memory
                compression_succeeded = True

                history = []
                history_after_compression = []

                print(
                    "Compression succeeded and "
                    "the state validated."
                )

                print(
                    json.dumps(
                        memory,
                        ensure_ascii=False,
                        indent=2,
                    )
                )

            except Exception as error:
                print("Compression failed.")
                print(f"Reason: {error}")
                print(
                    "History was preserved because "
                    "the compression did not succeed."
                )

            continue

        user_message = {
            "role": "user",
            "content": turn,
        }

        if compression_succeeded:
            history_after_compression.append(
                user_message
            )

            messages = build_compressed_messages(
                system_message,
                memory,
                history_after_compression,
            )

        else:
            history.append(user_message)

            messages = build_messages(
                system_message,
                history,
            )

        call_number += 1

        token_count = count_tokens(
            messages,
            encoder,
        )

        token_counts.append(token_count)

        print(
            f"Call {call_number}: "
            f"{token_count} tokens"
        )

        try:
            answer = call_assistant(
                client,
                messages,
            )

            assistant_message = {
                "role": "assistant",
                "content": answer,
            }

            if compression_succeeded:
                history_after_compression.append(
                    assistant_message
                )
            else:
                history.append(
                    assistant_message
                )

            print(f"  Assistant: {answer}")

        except Exception as error:
            print(f"  API call failed: {error}")

    probe_results = []

    print("\nRun B probes:")

    for probe in probes:
        if compression_succeeded:
            probe_messages = build_compressed_messages(
                system_message,
                memory,
                history_after_compression,
            )
        else:
            probe_messages = build_messages(
                system_message,
                history,
            )

        probe_messages.append(
            {
                "role": "user",
                "content": probe["question"],
            }
        )

        try:
            answer = call_assistant(
                client,
                probe_messages,
            )

            retrieved = check_probe(
                answer,
                probe["expect_contains"],
            )

            status = (
                "retrieved"
                if retrieved
                else "lost"
            )

            print(f"{probe['id']}: {status}")
            print(f"  Answer: {answer}")

            probe_results.append(
                {
                    "id": probe["id"],
                    "retrieved": retrieved,
                    "answer": answer,
                }
            )

        except Exception as error:
            print(
                f"{probe['id']}: could not run"
            )
            print(f"  Reason: {error}")

            probe_results.append(
                {
                    "id": probe["id"],
                    "retrieved": None,
                    "answer": None,
                }
            )

    return {
        "token_counts": token_counts,
        "peak": max(token_counts) if token_counts else 0,
        "total": sum(token_counts),
        "probes": probe_results,
        "memory": memory,
        "compression_succeeded": compression_succeeded,
    }


def print_summary(run_a, run_b):
    print("\n" + "=" * 70)
    print("TOKEN COMPARISON")
    print("=" * 70)

    maximum_calls = max(
        len(run_a["token_counts"]),
        len(run_b["token_counts"]),
    )

    print(
        f"{'Call':<10}"
        f"{'Run A':<15}"
        f"{'Run B':<15}"
    )

    print("-" * 40)

    for index in range(maximum_calls):
        a_value = (
            run_a["token_counts"][index]
            if index < len(run_a["token_counts"])
            else "-"
        )

        b_value = (
            run_b["token_counts"][index]
            if index < len(run_b["token_counts"])
            else "-"
        )

        print(
            f"{index + 1:<10}"
            f"{str(a_value):<15}"
            f"{str(b_value):<15}"
        )

    print("-" * 40)

    print(
        f"{'Peak':<10}"
        f"{run_a['peak']:<15}"
        f"{run_b['peak']:<15}"
    )

    print(
        f"{'Total':<10}"
        f"{run_a['total']:<15}"
        f"{run_b['total']:<15}"
    )

    print("\n" + "=" * 70)
    print("PROBE COMPARISON")
    print("=" * 70)

    print(
        f"{'Probe':<10}"
        f"{'Run A':<20}"
        f"{'Run B':<20}"
    )

    print("-" * 50)

    for index in range(
        min(
            len(run_a["probes"]),
            len(run_b["probes"]),
        )
    ):
        probe_a = run_a["probes"][index]
        probe_b = run_b["probes"][index]

        if probe_a["retrieved"] is None:
            a_status = "could not run"
        else:
            a_status = (
                "retrieved"
                if probe_a["retrieved"]
                else "lost"
            )

        if probe_b["retrieved"] is None:
            b_status = "could not run"
        else:
            b_status = (
                "retrieved"
                if probe_b["retrieved"]
                else "lost"
            )

        print(
            f"{probe_a['id']:<10}"
            f"{a_status:<20}"
            f"{b_status:<20}"
        )


def run_scripted_comparison():
    chat_script = load_json(
        CHAT_SCRIPT_PATH
    )

    schema = load_json(
        SCHEMA_PATH
    )

    policy = load_json(
        POLICY_PATH
    )

    records = load_json(
        RECORDS_PATH
    )

    client = create_client()
    encoder = get_encoder()

    system_message = build_system_message(
        policy,
        records,
    )

    print("=" * 70)
    print(
        "SUBLAB MEDIUM - CONVERSATION MEMORY"
    )
    print("=" * 70)

    print(f"Model: {MODEL}")

    run_a = run_uncompressed(
        chat_script,
        client,
        encoder,
        system_message,
    )

    run_b = run_compressed(
        chat_script,
        schema,
        client,
        encoder,
        system_message,
    )

    print_summary(
        run_a,
        run_b,
    )

    print("\n" + "=" * 70)
    print("COMPRESSED STATE")
    print("=" * 70)

    if run_b["memory"] is not None:
        print(
            json.dumps(
                run_b["memory"],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(
            "No compressed state was produced."
        )


def interactive_mode():
    schema = load_json(
        SCHEMA_PATH
    )

    policy = load_json(
        POLICY_PATH
    )

    records = load_json(
        RECORDS_PATH
    )

    client = create_client()
    encoder = get_encoder()

    system_message = build_system_message(
        policy,
        records,
    )

    history = []
    history_after_compression = []

    memory = None
    compression_succeeded = False

    last_call_tokens = 0

    print("=" * 70)
    print(
        "INTERACTIVE CONVERSATION MEMORY"
    )
    print("=" * 70)

    print(
        "Commands: compress, tokens, exit"
    )

    print(
        "Enter applicant messages one at a time.\n"
    )

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("Goodbye.")
            break

        if user_input.lower() == "tokens":
            print(
                f"Last call tokens: {last_call_tokens}"
            )
            continue

        if user_input.lower() == "compress":
            if compression_succeeded:
                source_history = (
                    history_after_compression
                )
            else:
                source_history = history

            try:
                new_memory = compress_conversation(
                    client,
                    source_history,
                    schema,
                )

                memory = new_memory
                compression_succeeded = True

                history = []
                history_after_compression = []

                print(
                    "\nCompression successful:"
                )

                print(
                    json.dumps(
                        memory,
                        ensure_ascii=False,
                        indent=2,
                    )
                )

            except Exception as error:
                print(
                    "\nCompression failed."
                )

                print(
                    f"Reason: {error}"
                )

                print(
                    "Conversation history was preserved."
                )

            continue

        user_message = {
            "role": "user",
            "content": user_input,
        }

        if compression_succeeded:
            history_after_compression.append(
                user_message
            )

            messages = build_compressed_messages(
                system_message,
                memory,
                history_after_compression,
            )

        else:
            history.append(
                user_message
            )

            messages = build_messages(
                system_message,
                history,
            )

        last_call_tokens = count_tokens(
            messages,
            encoder,
        )

        try:
            answer = call_assistant(
                client,
                messages,
            )

            assistant_message = {
                "role": "assistant",
                "content": answer,
            }

            if compression_succeeded:
                history_after_compression.append(
                    assistant_message
                )
            else:
                history.append(
                    assistant_message
                )

            print(f"Assistant: {answer}")

        except Exception as error:
            print(
                f"API call failed: {error}"
            )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Conversation memory compression "
            "for Sublab Medium."
        )
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help=(
            "Run the interactive conversation mode."
        ),
    )

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    else:
        run_scripted_comparison()


if __name__ == "__main__":
    main()