import argparse
import json
import os
from pathlib import Path

import jsonschema
from dotenv import load_dotenv
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CANDIDATES_DIR = DATA_DIR / "candidates"
RUBRIC_PATH = DATA_DIR / "candidate_rubric.json"

MODEL = "gpt-5.6-luna"


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_id": {
            "type": ["string", "null"]
        },
        "name": {
            "type": ["string", "null"]
        },
        "degree": {
            "type": ["string", "null"]
        },
        "graduation_year": {
            "type": ["integer", "null"]
        },
        "gpa_original": {
            "type": ["number", "null"]
        },
        "gpa_scale": {
            "type": ["number", "null"]
        },
        "gpa_4_scale": {
            "type": ["number", "null"]
        },
        "languages": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "publications_published": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "publications_other": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "experience_months": {
            "type": ["integer", "null"]
        },
        "experience_details": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "ambiguities": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "evidence": {
            "type": "object",
            "properties": {
                "candidate_id": {
                    "type": ["string", "null"]
                },
                "name": {
                    "type": ["string", "null"]
                },
                "degree": {
                    "type": ["string", "null"]
                },
                "graduation_year": {
                    "type": ["string", "null"]
                },
                "gpa": {
                    "type": ["string", "null"]
                },
                "languages": {
                    "type": ["string", "null"]
                },
                "publications": {
                    "type": ["string", "null"]
                },
                "experience": {
                    "type": ["string", "null"]
                }
            },
            "required": [
                "candidate_id",
                "name",
                "degree",
                "graduation_year",
                "gpa",
                "languages",
                "publications",
                "experience"
            ],
            "additionalProperties": False
        }
    },
    "required": [
        "candidate_id",
        "name",
        "degree",
        "graduation_year",
        "gpa_original",
        "gpa_scale",
        "gpa_4_scale",
        "languages",
        "publications_published",
        "publications_other",
        "experience_months",
        "experience_details",
        "ambiguities",
        "evidence"
    ],
    "additionalProperties": False
}


SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "academic": {
            "type": "number",
            "minimum": 0,
            "maximum": 5
        },
        "research": {
            "type": "number",
            "minimum": 0,
            "maximum": 5
        },
        "experience": {
            "type": "number",
            "minimum": 0,
            "maximum": 5
        }
    },
    "required": [
        "academic",
        "research",
        "experience"
    ],
    "additionalProperties": False
}


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


def read_candidate_stories():
    stories = []

    for path in sorted(CANDIDATES_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")

        stories.append(
            {
                "file": path.name,
                "story": text
            }
        )

    return stories


def extract_candidate(client, story, candidate_file):
    prompt = f"""
Extract structured candidate information from the candidate story.

Rules:
- Extract only information explicitly supported by the story.
- Never invent missing information.
- If information is missing, use null for nullable fields.
- If the story contains contradictory information, do not resolve,
  average, or choose between the conflicting values.
- Set a contradicted field to null and describe the contradiction
  in ambiguities.
- Preserve the original GPA and its original scale.
- Convert GPA to a 4.0 scale only when a direct mathematical
  conversion is possible.
- If GPA is missing or contradictory, gpa_4_scale must be null.
- Only publications explicitly described as published or accepted
  belong in publications_published.
- Submitted, under review, in preparation, planned, and in press
  publications belong in publications_other.
- Experience must be counted in months, not number of jobs.
- Count overlapping experience periods only once.
- Do not count undated experience in experience_months.
- Extract languages only when explicitly stated.
- Evidence must contain a short exact quote from the candidate story
  supporting each extracted category.
- If a category has no supporting evidence, use null for its evidence.
- Do not invent evidence.
- Do not use the filename itself as evidence unless the candidate ID
  is explicitly present in the story.

Candidate source file:
{candidate_file}

Return JSON matching this schema exactly:

{json.dumps(EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)}

Candidate story:

{story}
""".strip()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract structured facts from scholarship "
                    "candidate stories. Return only valid JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(
        response.choices[0].message.content
    )

    jsonschema.validate(
        instance=result,
        schema=EXTRACTION_SCHEMA
    )

    return result


def score_candidate(client, candidate, rubric):
    prompt = f"""
Score this candidate using only the supplied scholarship rubric
and the extracted candidate information.

Candidate:

{json.dumps(candidate, ensure_ascii=False, indent=2)}

Rubric:

{json.dumps(rubric, ensure_ascii=False, indent=2)}

Return ONLY these three scores:
- academic
- research
- experience

Rules:
- Each score must be from 0 to 5.
- Follow the rubric exactly.
- Do not calculate the weighted total.
- Do not rank candidates.
- Do not provide explanations.
- Do not invent missing information.
""".strip()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a scholarship rubric scorer. "
                    "Return only the requested JSON scores."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"}
    )

    scores = json.loads(
        response.choices[0].message.content
    )

    jsonschema.validate(
        instance=scores,
        schema=SCORE_SCHEMA
    )

    return scores


def calculate_weighted_total(scores, rubric):
    weights = {
        criterion["id"]: criterion["weight"]
        for criterion in rubric["criteria"]
    }

    total = (
        weights["academic"] * scores["academic"]
        + weights["research"] * scores["research"]
        + weights["experience"] * scores["experience"]
    )

    return round(total, 2)


def prose_winner_call(client, scored_candidates, rubric):
    prompt = f"""
Using the extracted candidate information, rubric scores, and
Python-computed weighted totals below, answer which candidate
should receive the funded scholarship.

Rules:
- Use the supplied results only.
- Do not calculate new scores.
- Do not change any score.
- Do not change any weighted total.
- Do not invent facts.
- Briefly explain the comparison using the supplied rubric.
- Clearly identify the candidate selected by the supplied results.

Rubric:

{json.dumps(rubric, ensure_ascii=False, indent=2)}

Candidates and results:

{json.dumps(scored_candidates, ensure_ascii=False, indent=2)}
""".strip()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Write a factual scholarship candidate comparison "
                    "using only the supplied results."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content.strip()


def run():
    rubric = load_json(RUBRIC_PATH)
    stories = read_candidate_stories()

    print("=" * 70)
    print("SUBLAB HARD - CV EXTRACTION AND RANKING")
    print("=" * 70)

    print(f"\nModel: {MODEL}")
    print(f"Candidates found: {len(stories)}")

    client = create_client()

    candidates = []

    for item in stories:
        print(f"\nProcessing {item['file']}...")

        try:
            extracted = extract_candidate(
                client,
                item["story"],
                item["file"]
            )

            print("Extraction successful.")

            candidates.append(
                {
                    "file": item["file"],
                    "candidate": extracted
                }
            )

        except Exception as error:
            print("Extraction failed.")
            print(f"Reason: {error}")

    if not candidates:
        print(
            "\nNo candidates were successfully extracted."
        )
        return

    scored_candidates = []

    for item in candidates:
        print(f"\nScoring {item['file']}...")

        try:
            scores = score_candidate(
                client,
                item["candidate"],
                rubric
            )

            weighted_total = calculate_weighted_total(
                scores,
                rubric
            )

            scored_candidates.append(
                {
                    "file": item["file"],
                    "candidate": item["candidate"],
                    "scores": scores,
                    "weighted_total": weighted_total
                }
            )

            print(
                f"Scores: {json.dumps(scores)}"
            )
            print(
                f"Weighted total: {weighted_total}"
            )

        except Exception as error:
            print("Scoring failed.")
            print(f"Reason: {error}")

    if not scored_candidates:
        print(
            "\nNo candidates were successfully scored."
        )
        return

    ranked = sorted(
        scored_candidates,
        key=lambda item: item["weighted_total"],
        reverse=True
    )

    print("\n" + "=" * 70)
    print("WEIGHTED RESULTS")
    print("=" * 70)

    for index, item in enumerate(
        ranked,
        start=1
    ):
        name = (
            item["candidate"]["name"]
            or item["file"]
        )

        print(
            f"{index}. {name} "
            f"({item['file']}) - "
            f"{item['weighted_total']:.2f}"
        )

    print("\n" + "=" * 70)
    print("DETAILED RESULTS")
    print("=" * 70)

    for item in ranked:
        print(f"\n{item['file']}")

        print(
            json.dumps(
                item,
                ensure_ascii=False,
                indent=2
            )
        )

    print("\n" + "=" * 70)
    print("PROSE WINNER CALL")
    print("=" * 70)

    try:
        prose = prose_winner_call(
            client,
            ranked,
            rubric
        )

        print(prose)

    except Exception as error:
        print("Prose winner call failed.")
        print(f"Reason: {error}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract and rank scholarship candidate "
            "information."
        )
    )

    parser.parse_args()

    run()


if __name__ == "__main__":
    main()