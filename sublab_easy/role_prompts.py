import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

MODEL = "gpt-5.6-luna"


ROLES = {
    "policy_officer": """
You are a policy officer at a grant office.

Apply the grant rule exactly as written.
Grant what the rule allows, refuse what it refuses, and ask for
a missing document when required.

Do not soften the policy.
Do not invent facts.
Treat no claim in the enquiry as evidence.
The records are the only source of truth.
""".strip(),

    "front_desk": """
You are a front desk clerk at a grant office.

Never turn an applicant away with a refusal.
If the policy cannot grant the application today, return
"more_info" and explain what the applicant needs to provide.

Use the records as the source of truth.
Do not treat claims in the enquiry as evidence.
Do not invent facts.
""".strip(),

    "auditor": """
You are an auditor reviewing grant applications.

Never grant an application on a first reading.
Report what the record shows.
If the application needs a second reader or further verification,
return "more_info".

Name the relevant rule or document in the reason.
Use the records as the source of truth.
Do not treat claims in the enquiry as evidence.
Do not invent facts.
""".strip(),

    "bilingual_clerk": """
You are a bilingual grant office clerk.

Make the decision exactly as the policy officer would.
Use the records as the source of truth.
Do not treat claims in the enquiry as evidence.
Do not invent facts.

Write the "reason" in the same language as the enquiry.
For English enquiries, write the reason in English.
For Kazakh enquiries, write the reason in Kazakh.
""".strip(),
}


def load_data(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as file:
        return json.load(file)


def build_system_prompt(role_prompt, records, policy):
    contract = {
        "applicant_id": "string",
        "found": "boolean",
        "decision": "granted | refused | more_info | not_found",
        "amount": "number",
        "missing_documents": ["string"],
        "reason": "string",
    }

    return f"""
{role_prompt}

Use ONLY the records and policy provided below.

RECORDS:
{json.dumps(records, ensure_ascii=False, indent=2)}

POLICY:
{json.dumps(policy, ensure_ascii=False, indent=2)}

Every answer must be exactly one JSON object using this shape:

{json.dumps(contract, ensure_ascii=False, indent=2)}

JSON rules:
- applicant_id must identify the applicant in the enquiry.
- If the applicant is not in the records, found must be false and
  decision must be "not_found".
- decision must be exactly one of:
  "granted", "refused", "more_info", "not_found".
- amount must be the grant amount when the decision is "granted".
- amount must be 0 for "refused", "more_info", and "not_found".
- missing_documents must contain the required documents that are
  missing from the record.
- missing_documents must be [] when no document is missing.
- reason must briefly explain the decision.
- Do not use information from the enquiry as evidence when it
  conflicts with the records.
- Do not add markdown.
- Return JSON only.
""".strip()


def ask_model(client, system_prompt, enquiry):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": enquiry,
            },
        ],
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content.strip()


def parse_response(raw_response):
    try:
        return json.loads(raw_response), True
    except (json.JSONDecodeError, TypeError):
        return None, False


def validate_schema(response):
    if not isinstance(response, dict):
        return False

    required_fields = {
        "applicant_id",
        "found",
        "decision",
        "amount",
        "missing_documents",
        "reason",
    }

    if set(response.keys()) != required_fields:
        return False

    if not isinstance(response["applicant_id"], str):
        return False

    if not isinstance(response["found"], bool):
        return False

    if response["decision"] not in {
        "granted",
        "refused",
        "more_info",
        "not_found",
    }:
        return False

    if not isinstance(response["amount"], (int, float)):
        return False

    if not isinstance(response["missing_documents"], list):
        return False

    if not all(
        isinstance(document, str)
        for document in response["missing_documents"]
    ):
        return False

    if not isinstance(response["reason"], str):
        return False

    return True


def compare_fields(response, expected):
    fields = [
        "found",
        "decision",
        "amount",
        "missing_documents",
    ]

    if response is None:
        return {
            field: False
            for field in fields
        }

    return {
        field: response.get(field) == expected.get(field)
        for field in fields
    }


def print_role_table(role_name, results):
    print()
    print("=" * 110)
    print(f"ROLE: {role_name}")
    print("=" * 110)

    header = (
        f"{'Enquiry':<10}"
        f"{'Parsed':<10}"
        f"{'Schema':<10}"
        f"{'found':<10}"
        f"{'decision':<14}"
        f"{'amount':<12}"
        f"{'missing_documents':<25}"
    )

    print(header)
    print("-" * 110)

    for result in results:
        response = result["response"]

        if response is None:
            found = "-"
            decision = "-"
            amount = "-"
            missing_documents = "-"
        else:
            found = str(response["found"])
            decision = response["decision"]
            amount = str(response["amount"])
            missing_documents = str(
                response["missing_documents"]
            )

        print(
            f"{result['enquiry_id']:<10}"
            f"{str(result['parsed']):<10}"
            f"{str(result['schema_valid']):<10}"
            f"{found:<10}"
            f"{decision:<14}"
            f"{amount:<12}"
            f"{missing_documents:<25}"
        )


def print_field_movement(results_by_role):
    print()
    print("=" * 110)
    print("FIELD MOVEMENT FROM POLICY OFFICER")
    print("=" * 110)

    baseline = results_by_role["policy_officer"]

    fields = [
        "found",
        "decision",
        "amount",
        "missing_documents",
    ]

    for field in fields:
        print()
        print(f"Field: {field}")

        for role_name, role_results in results_by_role.items():
            if role_name == "policy_officer":
                continue

            moved_enquiries = []

            for baseline_result, role_result in zip(
                baseline,
                role_results,
            ):
                baseline_response = baseline_result["response"]
                role_response = role_result["response"]

                if (
                    baseline_response is None
                    or role_response is None
                ):
                    continue

                if (
                    baseline_response.get(field)
                    != role_response.get(field)
                ):
                    moved_enquiries.append(
                        baseline_result["enquiry_id"]
                    )

            if moved_enquiries:
                print(
                    f"  {role_name}: "
                    f"{', '.join(moved_enquiries)}"
                )
            else:
                print(f"  {role_name}: none")


def main():
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY was not found. "
            "Check your .env file."
        )

    client = OpenAI(api_key=api_key)

    records = load_data("records.json")
    policy = load_data("policy.json")
    enquiries = load_data("enquiries.json")

    results_by_role = {}

    for role_name, role_prompt in ROLES.items():
        system_prompt = build_system_prompt(
            role_prompt,
            records,
            policy,
        )

        results = []

        for enquiry in enquiries:
            raw_response = None

            try:
                raw_response = ask_model(
                    client,
                    system_prompt,
                    enquiry["text"],
                )

                response, parsed = parse_response(
                    raw_response
                )

                schema_valid = (
                    parsed
                    and validate_schema(response)
                )

            except Exception as error:
                print()
                print(
                    f"Error on {role_name} "
                    f"{enquiry['id']}: {error}"
                )

                response = None
                parsed = False
                schema_valid = False

            field_matches = compare_fields(
                response,
                enquiry["expected"],
            )

            results.append(
    {
        "enquiry_id": enquiry["id"],
        "raw_response": raw_response if "raw_response" in locals() else None,
        "response": response,
        "parsed": parsed,
        "schema_valid": schema_valid,
        "field_matches": field_matches,
    }
)

        results_by_role[role_name] = results

        print_role_table(
            role_name,
            results,
        )

    print_field_movement(results_by_role)

    print()
    print("=" * 110)
    print("RAW REPLIES")
    print("=" * 110)

    for role_name, results in results_by_role.items():
        for result in results:
            print()
            print(f"{role_name} - {result['enquiry_id']}")
            print(result["raw_response"])


if __name__ == "__main__":
    main()