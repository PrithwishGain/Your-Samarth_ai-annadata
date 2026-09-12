import os
import asyncio
import httpx
import json

from fastapi import FastAPI, WebSocket, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client, Client

from crop_doctor import analyze_crop


# Load variables from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)

# Create FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:5502",
        "http://localhost:5502",
        "https://prithwishgain.github.io",
        "https://samarth.business",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Allow our frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:5502",
        "http://localhost:5502",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini client - initialize only if API key is present
gemini_api_key = os.getenv("GEMINI_API_KEY")
client = None
if gemini_api_key:
    client = genai.Client(
        api_key=gemini_api_key
    )

MODEL = "gemini-3.1-flash-live-preview"
TEXT_MODEL = "gemini-3.6-flash"


# -------------------------
# Health check
# -------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Samarth AI backend is running"
    }

# ============================================================
# ANNYADATA CROP DOCTOR API
# ============================================================

@app.post("/crop-doctor/analyze")
async def crop_doctor_analyze(
    image: UploadFile = File(...),
    crop: str = Form(...)
):
    """
    Analyze a crop image using the Annyadata Crop Doctor engine.

    The vision model performs the diagnosis.
    Samarth can later use the result to explain the diagnosis
    and provide farmer-friendly guidance.
    """

    try:
        # Read uploaded image
        image_bytes = await image.read()

        if not image_bytes:
            return {
                "success": False,
                "error": "No image was uploaded."
            }

        # Run Crop Doctor
        result = analyze_crop(
            image_bytes,
            crop.strip().lower()
        )

        return result

    except Exception as e:

        print(
            "Crop Doctor API error:",
            str(e)
        )

        return {
            "success": False,
            "error": str(e)
        }

# -------------------------
# Knowledge Base Search
# -------------------------

@app.get("/knowledge/search")
async def search_knowledge(query: str):

    try:
        query_lower = query.strip().lower()

        response = (
            supabase
            .table("knowledge_documents")
            .select(
                "id, source_id, title, category, subcategory, content, state, language, keywords, last_updated"
            )
            .or_(
                f"title.ilike.%{query_lower}%,"
                f"category.ilike.%{query_lower}%,"
                f"subcategory.ilike.%{query_lower}%,"
                f"content.ilike.%{query_lower}%,"
                f"keywords.ilike.%{query_lower}%"
            )
            .limit(5)
            .execute()
        )

        print("SEARCH QUERY:", query_lower)
        print("SUPABASE DATA:", response.data)

        return {
            "query": query,
            "results": response.data
        }

    except Exception as e:

        print("Knowledge search error:", str(e))

        return {
            "error": str(e)
        }

# -------------------------
# Generate Embeddings
# -------------------------

EMBEDDING_MODEL = "gemini-embedding-2"


def generate_embedding(text: str):

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768
        )
    )

    return result.embeddings[0].values

# -------------------------
# Gemini Function Tool
# Knowledge Base Search
# -------------------------

KNOWLEDGE_BASE_TOOL = {
    "function_declarations": [
        {
            "name": "search_knowledge_base",
            "description": """
Search Samarth AI's verified knowledge base.

Use this tool whenever information is needed from
Samarth's verified knowledge base.

The knowledge base may contain information about ANY topic,
including but not limited to:

- agriculture
- farming
- crops
- government schemes
- loans
- businesses
- vehicles
- machines
- products
- people
- places
- documents
- services
- rural development
- finance
- plans
- and other entities.

IMPORTANT CONTEXT RULE:

If the user's question refers to something mentioned
earlier in the conversation using words such as:

"this"
"that"
"it"
"its"
"they"
"them"
"their"
"same"
"above"
"this variety"
"this vehicle"
"this machine"
"that scheme"
"that product"

then use the previous conversation to identify the
actual entity.

The query sent to this tool MUST be self-contained.

For example:

Previous:
"Tell me about Samarth Golden-84729"

Current:
"How deep should this variety be planted?"

Correct tool query:
"How deep should Samarth Golden-84729 be planted?"

Do NOT send:
"How deep should this variety be planted?"

Do NOT ask the user to repeat the entity when it is
already known from the conversation.

This rule applies to every topic, not only agriculture.

Do not use this tool for casual conversation,
greetings, jokes, or general conversation.
""",
            
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {
                                "type": "STRING",
                                "description": """
                            The user's question or information request about ANY topic
                            covered by Samarth AI's knowledge base.

                            This is NOT limited to agriculture.

                            The query may refer to:
                            - agriculture
                            - crops
                            - farming
                            - government schemes
                            - loans
                            - businesses
                            - vehicles
                            - machines
                            - products
                            - people
                            - places
                            - documents
                            - services
                            - rural development
                            - finance
                            - plans
                            - or any other knowledge-base topic.

                            If the user asks a follow-up question about something
                            mentioned earlier, the query must still be resolved using
                            the previous conversation before searching.
                            """
                            }
                },
                "required": ["query"]
            }
        }
    ]
}

# -------------------------
# Gemini Function Tool
# Structured Government Scheme Search
# -------------------------

GOVERNMENT_SCHEME_TOOL = {
    "function_declarations": [
        {
            "name": "get_government_scheme",
            "description": """
Retrieve complete verified information about a specific
government scheme from Samarth's structured scheme database.

Use this tool when the user asks detailed questions about a
specific government scheme, including:

- scheme benefits
- subsidy or financial assistance
- eligibility
- required documents
- application process
- application links
- official sources
- scheme conditions
- related schemes

The scheme must be identified using its scheme_id.

Known scheme IDs may include:
- PMFME
- PMMY
- PMEGP
- PM-KISAN
- PMVISHWAKARMA
- PMSVANIDHI
- AIF

Do not invent a scheme_id.
""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "scheme_id": {
                        "type": "STRING",
                        "description": """
The exact scheme_id of the government scheme being requested.
For example: PMFME, PMMY, PMEGP, PM-KISAN, AIF.
"""
                    }
                },
                "required": ["scheme_id"]
            }
        }
    ]
}

# -------------------------
# Generic Conversation Context Resolver
# -------------------------

async def resolve_contextual_query(query: str, conversation_history=None):
    """
    Convert a contextual/follow-up query into a self-contained query
    using the previous conversation.

    This is generic and is NOT limited to agriculture.
    """

    if not query:
        return query

    if not conversation_history:
        return query

    try:
        # Use recent conversation for context
        history_text = "\n".join(conversation_history[-12:])

        prompt = f"""
You are a conversation context resolver for Samarth AI.

Your job is to rewrite the user's latest query so that it is
fully understandable without needing the previous conversation.

IMPORTANT RULES:

1. Use the previous conversation to resolve references such as:
   - this
   - that
   - it
   - they
   - them
   - this variety
   - this vehicle
   - this machine
   - the same one
   - the above
   - that scheme
   - that person
   - that product
   - or any similar contextual reference.

2. If the latest query already contains all necessary information,
   return it unchanged.

3. Do NOT answer the question.

4. Do NOT add information that was not present in the conversation.

5. Do NOT assume an entity if the conversation does not provide one.

6. Make the result a natural, self-contained search/query sentence.

7. This must work for ANY topic, not only agriculture.

PREVIOUS CONVERSATION:
{history_text}

LATEST QUERY:
{query}

RETURN ONLY THE REWRITTEN QUERY.
"""

        result = await asyncio.to_thread(
            client.models.generate_content,
            model=TEXT_MODEL,
            contents=prompt
        )

        resolved = (result.text or "").strip()

        if resolved:
            print("CONTEXT RESOLVED QUERY:", resolved)
            return resolved

        return query

    except Exception as e:
        print("CONTEXT RESOLUTION ERROR:", str(e))
        return query


async def search_knowledge_base_tool(
    query: str,
    conversation_history=None
):
    """
    Generate an embedding for the user's query
    and search the Supabase vector knowledge base.
    """

    try:
        search_query = query


        print("RAW QUERY:", query)
        print("CONTEXT SEARCH QUERY:", search_query)

        print("\n==============================")
        print("KNOWLEDGE TOOL CALLED")
        print("QUERY:", query)
        print("==============================")

        # Generate 768-dimensional query embedding
        embedding = await asyncio.to_thread(
        generate_embedding,
        search_query
    )

        print("QUERY EMBEDDING GENERATED:", len(embedding))

        # Call Supabase vector similarity function
        response = await asyncio.to_thread(
            lambda: supabase.rpc(
                "match_knowledge_documents",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.20,
                    "match_count": 5
                }
            ).execute()
        )

        documents = response.data or []

        print("VECTOR SEARCH RESULTS:", len(documents))

        for doc in documents:
            print(
                " -",
                doc.get("title"),
                "| similarity:",
                doc.get("similarity")
            )

        # Keep only information Gemini actually needs
        results = []

        for doc in documents:
            results.append({
                "title": doc.get("title"),
                "category": doc.get("category"),
                "subcategory": doc.get("subcategory"),
                "content": doc.get("content"),
                "state": doc.get("state"),
                "language": doc.get("language"),
                "keywords": doc.get("keywords"),
                "similarity": doc.get("similarity")
            })

        return {
            "query": search_query,
            "results": results
        }

    except Exception as e:

        print("KNOWLEDGE TOOL ERROR:", str(e))

        return {
            "error": str(e),
            "results": []
        }

# -------------------------
# Structured Government Scheme Search
# -------------------------

async def get_government_scheme(scheme_id: str):
    """
    Retrieve a complete government scheme from the
    structured scheme database.

    This is generic and works for every scheme using
    its scheme_id.
    """

    try:
        # ---------------------------------------------
        # 1. Get main scheme record
        # ---------------------------------------------

        scheme_response = await asyncio.to_thread(
            lambda: supabase
            .table("government_schemes")
            .select("*")
            .eq("scheme_id", scheme_id)
            .limit(1)
            .execute()
        )

        schemes = scheme_response.data or []

        if not schemes:
            return {
                "scheme_id": scheme_id,
                "found": False,
                "scheme": None
            }

        scheme = schemes[0]

        # ---------------------------------------------
        # 2. Get scheme benefits
        # ---------------------------------------------

        benefits_response = await asyncio.to_thread(
            lambda: supabase
            .table("scheme_benefits")
            .select("*")
            .eq("scheme_id", scheme_id)
            .execute()
        )

        benefits = benefits_response.data or []

        # ---------------------------------------------
        # 3. Get eligibility rules
        # ---------------------------------------------

        eligibility_response = await asyncio.to_thread(
            lambda: supabase
            .table("scheme_eligibility_rules")
            .select("*")
            .eq("scheme_id", scheme_id)
            .execute()
        )

        eligibility_rules = eligibility_response.data or []

        # ---------------------------------------------
        # 4. Get required documents
        # ---------------------------------------------

        documents_response = await asyncio.to_thread(
            lambda: supabase
            .table("scheme_documents")
            .select("*")
            .eq("scheme_id", scheme_id)
            .execute()
        )

        documents = documents_response.data or []

        # ---------------------------------------------
        # 5. Get verified sources
        # ---------------------------------------------

        sources_response = await asyncio.to_thread(
            lambda: supabase
            .table("scheme_sources")
            .select("*")
            .eq("scheme_id", scheme_id)
            .execute()
        )

        sources = sources_response.data or []

        # ---------------------------------------------
        # 6. Get scheme relationships
        # ---------------------------------------------

        relationships_response = await asyncio.to_thread(
            lambda: supabase
            .table("scheme_relationships")
            .select("*")
            .eq("scheme_id", scheme_id)
            .execute()
        )

        relationships = relationships_response.data or []

        # ---------------------------------------------
        # 7. Return complete structured scheme
        # ---------------------------------------------

        result = {
            "scheme_id": scheme_id,
            "found": True,
            "scheme": scheme,
            "benefits": benefits,
            "eligibility_rules": eligibility_rules,
            "documents": documents,
            "sources": sources,
            "relationships": relationships
        }

        print("\n================================")
        print("STRUCTURED SCHEME RETRIEVED")
        print("================================")
        print("SCHEME:", scheme.get("scheme_name"))
        print("BENEFITS:", len(benefits))
        print("ELIGIBILITY RULES:", len(eligibility_rules))
        print("DOCUMENTS:", len(documents))
        print("SOURCES:", len(sources))
        print("RELATIONSHIPS:", len(relationships))
        print("================================\n")

        return result

    except Exception as e:
        print("STRUCTURED SCHEME SEARCH ERROR:", str(e))

        return {
            "scheme_id": scheme_id,
            "found": False,
            "scheme": None,
            "benefits": [],
            "eligibility_rules": [],
            "documents": [],
            "sources": [],
            "relationships": [],
            "error": str(e)
        }


# -------------------------
# Government Scheme Eligibility Evaluator
# -------------------------

def evaluate_scheme_rule(rule, user_data):
    """
    Evaluate one structured eligibility rule against user data.

    Returns:
        PASS
        FAIL
        UNKNOWN
    """

    field_name = rule.get("field_name")
    operator = rule.get("operator")
    expected_value = rule.get("expected_value")

    if not field_name or not operator:
        return "UNKNOWN"

    # User has not provided the information required
    # to evaluate this rule.
    if field_name not in user_data:
        return "UNKNOWN"

    actual_value = user_data.get(field_name)

    if actual_value is None or actual_value == "":
        return "UNKNOWN"

    try:
        # Normalize operator
        op = str(operator).strip().lower()

        # ---------------------------------------------
        # Equality
        # ---------------------------------------------

        if op in ["=", "==", "equals", "equal"]:
            return "PASS" if actual_value == expected_value else "FAIL"

        # ---------------------------------------------
        # Not equal
        # ---------------------------------------------

        if op in ["!=", "not_equals", "not_equal"]:
            return "PASS" if actual_value != expected_value else "FAIL"

        # ---------------------------------------------
        # Greater than
        # ---------------------------------------------

        if op in [">", "greater_than"]:
            return "PASS" if float(actual_value) > float(expected_value) else "FAIL"

        # ---------------------------------------------
        # Greater than or equal
        # ---------------------------------------------

        if op in [
            ">=",
            "greater_than_or_equal",
            "greater_than_or_equal_to"
        ]:
            return "PASS" if float(actual_value) >= float(expected_value) else "FAIL"

        # ---------------------------------------------
        # Less than
        # ---------------------------------------------

        if op in ["<", "less_than"]:
            return "PASS" if float(actual_value) < float(expected_value) else "FAIL"

        # ---------------------------------------------
        # Less than or equal
        # ---------------------------------------------

        if op in [
            "<=",
            "less_than_or_equal",
            "less_than_or_equal_to"
        ]:
            return "PASS" if float(actual_value) <= float(expected_value) else "FAIL"

        # ---------------------------------------------
        # IN
        # ---------------------------------------------

        if op == "in":

            values = expected_value

            if isinstance(values, str):
                try:
                    values = json.loads(values)
                except Exception:
                    values = [
                        item.strip()
                        for item in values.split(",")
                    ]

            if not isinstance(values, list):
                return "UNKNOWN"

            return "PASS" if actual_value in values else "FAIL"

        # ---------------------------------------------
        # NOT IN
        # ---------------------------------------------

        if op == "not_in":

            values = expected_value

            if isinstance(values, str):
                try:
                    values = json.loads(values)
                except Exception:
                    values = [
                        item.strip()
                        for item in values.split(",")
                    ]

            if not isinstance(values, list):
                return "UNKNOWN"

            return "PASS" if actual_value not in values else "FAIL"

        # ---------------------------------------------
        # Boolean conditions
        # ---------------------------------------------

        if op in ["is_true", "true"]:

            if isinstance(actual_value, str):
                actual_value = actual_value.strip().lower() == "true"

            return "PASS" if actual_value is True else "FAIL"

        if op in ["is_false", "false"]:

            if isinstance(actual_value, str):
                actual_value = actual_value.strip().lower() == "true"

            return "PASS" if actual_value is False else "FAIL"

        # ---------------------------------------------
        # Special scheme-rule operators
        # ---------------------------------------------

        # The scheme explicitly says that this condition
        # is NOT required. It should never make a user fail.
        if op == "not_required":
            return "PASS"


        # A "required" rule means the supplied user value
        # must satisfy the expected value.
        if op == "required":

            if isinstance(expected_value, bool):

                if isinstance(actual_value, str):
                    normalized = actual_value.strip().lower()

                    if normalized in ["true", "yes", "1"]:
                        actual_value = True
                    elif normalized in ["false", "no", "0"]:
                        actual_value = False

                return "PASS" if actual_value is expected_value else "FAIL"

            return "PASS" if actual_value == expected_value else "FAIL"


        # "preferred" is a ranking/preference condition,
        # NOT a hard eligibility condition.
        #
        # Therefore, failing a preference must never
        # make the user ineligible.
        if op == "preferred":

            values = expected_value

            if isinstance(values, str):
                try:
                    values = json.loads(values)
                except Exception:
                    values = [values]

            if isinstance(values, list):
                if actual_value in values:
                    return "PASS"
                return "UNKNOWN"

            if actual_value == values:
                return "PASS"

            return "UNKNOWN"


        # This condition applies specifically to a
        # subsidy component and cannot be evaluated
        # without knowing which benefit the user wants.
        if op == "required_for_subsidy":
            return "UNKNOWN"


        # ---------------------------------------------
        # Other semantic operators
        # ---------------------------------------------

        if op in [
            "depends_on",
            "conditional",
            "less_than_or_equal_to_annual_turnover",
            "project_cost_vs_turnover"
        ]:
            return "UNKNOWN"

        # ---------------------------------------------
        # Unsupported operator
        # ---------------------------------------------

        return "UNKNOWN"

    except (ValueError, TypeError):
        return "UNKNOWN"


def evaluate_scheme_rules(rules, user_data):
    """
    Evaluate all eligibility rules for a scheme.

    Returns detailed results instead of making an
    immediate eligibility claim.
    """

    results = []

    passed = 0
    failed = 0
    unknown = 0

    for rule in rules:

        result = evaluate_scheme_rule(
            rule,
            user_data
        )

        if result == "PASS":
            passed += 1

        elif result == "FAIL":
            failed += 1

        else:
            unknown += 1

        results.append({
            "rule_id": rule.get("rule_id"),
            "rule_type": rule.get("rule_type"),
            "field_name": rule.get("field_name"),
            "operator": rule.get("operator"),
            "expected_value": rule.get("expected_value"),
            "mandatory": rule.get("mandatory"),
            "exclusion_rule": rule.get("exclusion_rule"),
            "priority": rule.get("priority"),
            "result": result,
            "rule_description": rule.get("rule_description")
        })

    return {
        "total_rules": len(rules),
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "results": results
    }

# -------------------------
# Overall Scheme Eligibility Assessment
# -------------------------

def assess_scheme_eligibility(rules, user_data):
    """
    Evaluate a scheme's rules and produce a safe overall assessment.

    Possible assessments:

    - eligible
    - potentially_eligible
    - needs_more_information
    - not_eligible

    The function never claims eligibility when required
    information is still unknown.
    """

    evaluation = evaluate_scheme_rules(
        rules,
        user_data
    )

    hard_failures = []
    unknown_mandatory = []
    preferences_passed = 0
    preferences_unknown = 0

    for result in evaluation["results"]:

        rule_result = result["result"]
        operator = str(result.get("operator") or "").strip().lower()
        mandatory = result.get("mandatory") is True
        exclusion_rule = result.get("exclusion_rule") is True

        # ---------------------------------------------
        # Hard exclusion rule
        # ---------------------------------------------

        if exclusion_rule and rule_result == "FAIL":
            hard_failures.append(result)
            continue

        # ---------------------------------------------
        # Mandatory eligibility failure
        # ---------------------------------------------

        if mandatory and rule_result == "FAIL":
            hard_failures.append(result)
            continue

        # ---------------------------------------------
        # Missing mandatory information
        # ---------------------------------------------

        if mandatory and rule_result == "UNKNOWN":
            unknown_mandatory.append(result)

        # ---------------------------------------------
        # Preference rules
        # ---------------------------------------------

        if operator == "preferred":

            if rule_result == "PASS":
                preferences_passed += 1

            elif rule_result == "UNKNOWN":
                preferences_unknown += 1

    # ---------------------------------------------
    # Overall assessment
    # ---------------------------------------------

    if hard_failures:
        assessment = "not_eligible"

    elif unknown_mandatory:
        assessment = "needs_more_information"

    elif evaluation["unknown"] > 0:
        assessment = "potentially_eligible"

    else:
        assessment = "eligible"

    # ---------------------------------------------
    # Human-readable explanation
    # ---------------------------------------------

    if assessment == "not_eligible":

        explanation = (
            "One or more mandatory eligibility or exclusion "
            "conditions are not satisfied."
        )

    elif assessment == "needs_more_information":

        explanation = (
            "The available information is not sufficient to "
            "determine eligibility because one or more mandatory "
            "conditions are still unknown."
        )

    elif assessment == "potentially_eligible":

        explanation = (
            "No mandatory condition has failed, but some "
            "conditions still need to be verified."
        )

    else:

        explanation = (
            "All evaluated mandatory eligibility conditions "
            "are satisfied."
        )

    return {
        "assessment": assessment,
        "explanation": explanation,

        "total_rules": evaluation["total_rules"],
        "passed": evaluation["passed"],
        "failed": evaluation["failed"],
        "unknown": evaluation["unknown"],

        "hard_failures": hard_failures,
        "unknown_mandatory": unknown_mandatory,

        "preferences_passed": preferences_passed,
        "preferences_unknown": preferences_unknown,

        "rule_results": evaluation["results"]
    }

@app.post("/knowledge/generate-embeddings")
async def generate_embeddings():

    try:

        if not client:
            return {
                "error": "Gemini API key is not configured."
            }

        response = (
            supabase
            .table("knowledge_documents")
            .select(
                "id, title, category, subcategory, content, state, language, keywords"
            )
            .execute()
        )

        documents = response.data or []

        updated = 0

        for doc in documents:

            text = f"""
Title: {doc.get('title', '')}
Category: {doc.get('category', '')}
Subcategory: {doc.get('subcategory', '')}
Content: {doc.get('content', '')}
State: {doc.get('state', '')}
Language: {doc.get('language', '')}
Keywords: {doc.get('keywords', '')}
""".strip()

            embedding = generate_embedding(text)

            (
                supabase
                .table("knowledge_documents")
                .update({
                    "embedding": embedding
                })
                .eq("id", doc["id"])
                .execute()
            )

            updated += 1

            print(
                f"Embedded: {doc.get('title')} "
                f"({len(embedding)} dimensions)"
            )

        return {
            "message": "Embeddings generated successfully",
            "documents_updated": updated
        }

    except Exception as e:

        print("Embedding generation error:", str(e))

        return {
            "error": str(e)
        }
                
# -------------------------
# AI Question Answering
# Supabase Vector Search + Gemini RAG
# -------------------------

@app.get("/ask")
async def ask_samarth(question: str):

    try:

        # Check Gemini API
        if not client:
            return {
                "error": "Gemini API key is not configured."
            }

        # -------------------------------------------------
        # 1. Generate embedding for user's question
        # -------------------------------------------------

        print("QUESTION:", question)

        query_embedding = generate_embedding(question)

        print(
            "QUERY EMBEDDING GENERATED:",
            len(query_embedding),
            "dimensions"
        )

        # -------------------------------------------------
        # 2. Search Supabase using vector similarity
        # -------------------------------------------------

        response = supabase.rpc(
            "match_knowledge_documents",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.20,
                "match_count": 5
            }
        ).execute()

        documents = response.data or []

        print("VECTOR SEARCH RESULTS:", documents)

        # -------------------------------------------------
        # 3. Convert results into Gemini context
        # -------------------------------------------------

        if documents:

            knowledge_context = "\n\n".join(
                [
                    f"""
Title: {doc.get('title', '')}
Category: {doc.get('category', '')}
Subcategory: {doc.get('subcategory', '')}
Content: {doc.get('content', '')}
State: {doc.get('state', '')}
Language: {doc.get('language', '')}
Keywords: {doc.get('keywords', '')}
"""
                    for doc in documents
                ]
            )

        else:

            knowledge_context = (
                "No relevant information was found "
                "in the Samarth knowledge base."
            )

        # -------------------------------------------------
        # 4. Create Gemini RAG prompt
        # -------------------------------------------------

        prompt = f"""
You are Samarth AI, an AI assistant designed to help
Indian farmers and rural entrepreneurs.

Answer the user's question using the knowledge base
provided below.

IMPORTANT RULES:

- Prefer information from the knowledge base.
- Do not invent specific government schemes,
  eligibility rules, interest rates, agricultural
  recommendations, or numbers.
- If the knowledge base does not contain enough
  information, clearly say that more information
  is needed.
- Give a simple and practical answer.
- Use easy language suitable for farmers.
- If the user asks about a government scheme or
  financial product, advise them to verify current
  eligibility and terms with the official authority
  or relevant institution.

KNOWLEDGE BASE:
{knowledge_context}

USER QUESTION:
{question}

Now answer the user.
"""

        # -------------------------------------------------
        # 5. Ask Gemini
        # -------------------------------------------------

        gemini_response = client.models.generate_content(
            model=TEXT_MODEL,
            contents=prompt
        )

        answer = gemini_response.text

        # -------------------------------------------------
        # 6. Return answer + sources
        # -------------------------------------------------

        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "title": doc.get("title"),
                    "category": doc.get("category"),
                    "subcategory": doc.get("subcategory"),
                    "similarity": doc.get("similarity")
                }
                for doc in documents
            ]
        }

    except Exception as e:

        print("AI question error:", str(e))

        return {
            "error": str(e)
        }

# -------------------------
# Weather API
# -------------------------

@app.get("/weather")
async def get_weather(latitude: float, longitude: float):
    """
    Fetch weather data for given coordinates using Open-Meteo API.
    Also reverse geocode to get location name using geocoding service.
    """
    try:
        # Fetch weather data from Open-Meteo API
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto"
        }
        
        async with httpx.AsyncClient() as client:
            weather_response = await client.get(weather_url, params=weather_params)
            weather_data = weather_response.json()
            
            # Get current weather
            current = weather_data.get("current", {})
            
            # Reverse geocode to get location name
            geocoding_url = "https://nominatim.openstreetmap.org/reverse"
            geocoding_params = {
                "lat": latitude,
                "lon": longitude,
                "format": "json"
            }
            
            geocoding_response = await client.get(
                geocoding_url, 
                params=geocoding_params,
                headers={"User-Agent": "Samarth-AI"}
            )
            geocoding_data = geocoding_response.json()
            
            # Extract location details
            address = geocoding_data.get("address", {})
            location_name = address.get("city") or address.get("town") or address.get("village") or "Unknown"
            state = address.get("state", "")
            
            if state:
                location_display = f"{location_name}, {state}"
            else:
                location_display = location_name
            
            # Interpret weather code
            weather_code = current.get("weather_code", 0)
            weather_description = interpret_weather_code(weather_code)
            
            # Estimate rain chance based on weather code
            rain_chance = estimate_rain_chance(weather_code)
            
            # Get best time for spraying
            spraying_recommendation = get_spraying_recommendation(
                weather_code,
                current.get("wind_speed_10m", 0),
                current.get("relative_humidity_2m", 0)
            )
            
            return {
                "location": location_display,
                "latitude": latitude,
                "longitude": longitude,
                "temperature": round(current.get("temperature_2m", 0)),
                "condition": weather_description,
                "humidity": current.get("relative_humidity_2m", 0),
                "wind_speed": round(current.get("wind_speed_10m", 0)),
                "rain_chance": rain_chance,
                "spraying_recommendation": spraying_recommendation,
                "advice": get_farming_advice(weather_code, rain_chance)
            }
            
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to fetch weather data"
        }


def interpret_weather_code(code: int) -> str:
    """Convert WMO weather codes to human-readable descriptions."""
    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Foggy",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with hail"
    }
    return codes.get(code, "Unknown")


def estimate_rain_chance(code: int) -> int:
    """Estimate rain chance based on weather code."""
    if code in [0, 1]:
        return 0
    elif code == 2:
        return 10
    elif code == 3:
        return 20
    elif code in [45, 48]:
        return 5
    elif code in [51, 53, 55]:
        return 40
    elif code in [61, 63, 65]:
        return 70
    elif code in [80, 81, 82]:
        return 60
    elif code in [95, 96, 99]:
        return 90
    else:
        return 30


def get_spraying_recommendation(code: int, wind_speed: float, humidity: float) -> str:
    """Provide farming-specific recommendations for spraying."""
    # Not ideal conditions for spraying:
    # - Rain/thunderstorm
    # - Strong wind (>15 km/h)
    # - High humidity (>85%)
    # - Fog
    
    if code in [61, 63, 65, 80, 81, 82, 95, 96, 99]:
        return "Not ideal"
    if wind_speed > 15:
        return "Wait - too windy"
    if humidity > 85:
        return "Not ideal"
    if code in [45, 48]:
        return "Not ideal"
    
    return "Good time"


def get_farming_advice(code: int, rain_chance: int) -> str:
    """Provide farming-specific advice based on weather."""
    if code in [61, 63, 65, 80, 81, 82, 95, 96, 99]:
        return "Rain expected — ideal day to apply nutrients but wait for heavy rain to pass."
    if rain_chance > 50:
        return f"Rain chance {rain_chance}% — consider delaying pesticide spray."
    if code in [0, 1, 2]:
        return "Clear weather — good day for field work and pesticide application."
    if code in [45, 48]:
        return "Foggy conditions — wait for visibility to improve before spraying."
    
    return "Monitor weather and plan accordingly."




# -------------------------
# Gemini Live WebSocket
# -------------------------

@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()

    # Keep conversation context for this voice session
    conversation_history = []


    print("Browser connected to /ws/voice")

    # Check if Gemini API key is available
    if not client:
        print("Gemini API key not configured")
        await websocket.send_json({
            "type": "error",
            "message": "Gemini API key is not configured. Please set GEMINI_API_KEY in .env"
        })
        await websocket.close()
        return

    config = {
    "response_modalities": ["AUDIO"],

    "input_audio_transcription": {},

    "output_audio_transcription": {},

        "realtime_input_config": {
        "automatic_activity_detection": {
            "disabled": True
        }
    },

    "tools": [
            KNOWLEDGE_BASE_TOOL,
            GOVERNMENT_SCHEME_TOOL
        ],

    


    "system_instruction": """
You are Samarth AI.

You are a helpful voice assistant for Indian farmers
and rural entrepreneurs.

Speak naturally and simply.

IMPORTANT KNOWLEDGE RULES:

1. When the user asks for factual information that may be
available in Samarth's verified knowledge base, use the
search_knowledge_base tool.

2. The knowledge base is NOT limited to agriculture.

It may contain information about:
- agriculture
- farming
- crops
- government schemes
- loans
- businesses
- vehicles
- machines
- products
- people
- places
- documents
- services
- rural development
- finance
- plans
- and other entities or topics.

3. If the user's question is a follow-up to something
mentioned earlier in the conversation and the answer may
require the knowledge base, you MUST call
search_knowledge_base.

4. NEVER ask the user to repeat an entity that was already
clearly mentioned earlier in the conversation.

5. Before calling search_knowledge_base, identify the entity
being referred to from the previous conversation and include
that entity in the tool query.

6. For example:

User:
"Tell me about Samarth Golden-84729"

User:
"How deep should this variety be planted?"

You MUST call search_knowledge_base.

The tool query must contain:
"Samarth Golden-84729"

Do NOT ask:
"Which variety?"

7. This contextual reasoning applies to EVERY topic,
not only agriculture.

8. After receiving knowledge-base results, answer using those
results.

9. Do not invent specific facts that are not supported by
the knowledge base.

10. If the question is casual conversation and does not
require factual knowledge, answer naturally without calling
the knowledge tool.

STRUCTURED GOVERNMENT SCHEME RULES:

11. When the user asks about a specific government scheme,
prefer the structured government scheme tool
get_government_scheme.

12. Use get_government_scheme when the user asks about:
- a specific scheme's benefits
- subsidy or financial assistance
- eligibility
- required documents
- application process
- application URL
- official sources
- scheme conditions
- scheme details

13. If the user clearly mentions a known scheme such as:
- PMFME
- PMMY
- PMEGP
- PM-KISAN
- PM Vishwakarma
- PM SVANidhi
- AIF

identify the corresponding scheme_id and use
get_government_scheme.

14. Do not use a guessed scheme_id.
If the scheme cannot be identified confidently,
use the general knowledge-base tool or ask for clarification.

15. After receiving structured scheme information,
use the returned benefits, eligibility rules, documents,
sources, and scheme details to answer the user.

16. Do not invent eligibility conditions, benefits,
amounts, deadlines, documents, application details,
or other scheme-specific facts.

17. When structured scheme information is available,
prefer it over general model knowledge for scheme-specific
answers.

18. If the user asks which government schemes may be
suitable for their personal situation rather than asking
about one specific scheme, do not assume that one scheme
is suitable. Use the available user context and relevant
verified information to determine what additional
information is needed.

CONVERSATION MEMORY RULES:

19. Remember the entire current conversation.

20. Use previous user and Samarth messages when interpreting
follow-up questions.

21. A question is contextual when it refers to something
mentioned earlier using words such as:

"this", "that", "it", "its", "they", "them",
"their", "same", "above", "this variety",
"this vehicle", "this machine", "that scheme",
"that product", "that person", or similar references.

22. If the latest question is contextual, resolve the
reference using the previous conversation.

23. If the referenced entity is unambiguous, DO NOT ask the
user to identify it again.

24. If the contextual question requires knowledge-base
information, you MUST call search_knowledge_base.

25. The search_knowledge_base query MUST be completely
self-contained.

26. Replace contextual references with the actual entity.

27. Example:

User:
"Tell me about Samarth Golden-84729."

User:
"How deep should this variety be planted?"

Interpret "this variety" as:
"Samarth Golden-84729"

Call the knowledge tool with:
"How deep should Samarth Golden-84729 be planted?"

28. This rule applies to EVERY topic.

29. Example:

User:
"Tell me about a Mahindra tractor."

User:
"What is its engine capacity?"

Interpret "its" as the Mahindra tractor.

Call the knowledge tool with a self-contained query
containing the Mahindra tractor.

30. Example:

User:
"Tell me about PM-KISAN."

User:
"Who is eligible?"

Interpret the second question as:
"Who is eligible for PM-KISAN?"

31. If the previous conversation provides an unambiguous
entity, use it rather than asking for clarification.

32. Do not answer a contextual knowledge-base question
before attempting the knowledge-base search.

RECOMMENDATION RULES:

33. When the user asks for recommendations based on
their personal situation, such as:
- "Which government schemes are relevant to me?"
- "What schemes can I get?"
- "Which loan options suit me?"
- "What support can I get?"

you MUST use the knowledge-base results to form the answer.

34. Carefully inspect the titles AND content of the
knowledge-base results before answering.

35. Identify the 2–3 most relevant results for the
user's specific situation.

36. Prefer the strongest relevant knowledge-base results
over weaker or unrelated results.

37. Explicitly name the relevant schemes, programs,
loans, or support options found in the knowledge base.

38. For each recommended option, briefly explain WHY it
may be relevant to the user's provided context.

39. If a retrieved result is a general support document
rather than a specific scheme, describe it accurately
as support or a program instead of inventing a scheme name.

40. Do not ignore a highly relevant knowledge-base result
when forming the recommendation.

41. Distinguish carefully between:
- "potentially relevant"
- "appears suitable"
- "eligible"

Do NOT claim that the user is eligible unless the
knowledge-base information clearly establishes their
eligibility.

42. If the available knowledge-base information is not
enough to determine eligibility, say so clearly and ask
the user for the missing information through a natural
follow-up question.

43. When multiple relevant options are found, present
them as a short numbered list, with the most relevant
options first.

44. Do not give a vague recommendation when specific
relevant information is present in the knowledge-base
results.

45. Never invent a scheme name, eligibility condition,
benefit, amount, deadline, interest rate, or other
specific fact that is not supported by the knowledge base.

"""
}

    # -------------------------------------------------
    # Business context received from the frontend
    # -------------------------------------------------

    business_context_raw = websocket.query_params.get(
        "business_context"
    )

    if business_context_raw:

        try:

            business_context = json.loads(
                business_context_raw
            )

            intent = business_context.get(
                "intent",
                "unknown"
            )

            context_data = {
                key: value
                for key, value in business_context.items()
                if key != "intent"
            }

            context_instruction = f"""

CURRENT USER CONTEXT:

The user is currently using Samarth's
"{intent}" conversation.

The following information was provided by the
user through the initial form:

{json.dumps(
    context_data,
    ensure_ascii=False,
    indent=2
)}

IMPORTANT:

Use the information above as context when
answering the user's questions.

Do not ask the user to repeat information
that has already been provided.

Personalize your answers according to the
user's current context and intent.

If the user asks a question related to their
specific situation, use the provided information
to make the answer relevant to them.

If more information is genuinely required,
ask a natural follow-up question.

Do not assume information that was not provided.
"""

            config["system_instruction"] += (
                context_instruction
            )

            print(
                "BUSINESS CONTEXT LOADED:",
                business_context
            )

        except Exception as error:

            print(
                "Could not load business context:",
                repr(error)
            )

    try:
        async with client.aio.live.connect(
            model=MODEL,
            config=config
        ) as session:

            print("Gemini Live session connected!")

            await websocket.send_json({
                "type": "connected",
                "message": "Samarth is connected to Gemini Live"
            })

            async def receive_all_gemini_responses():
                while True:
                    response = await session._receive()

                    if response is None:
                        break

                    yield response


            async def receive_from_gemini():
                print("GEMINI RECEIVE LOOP STARTED")

                async for response in receive_all_gemini_responses():

                    # =====================================================
                    # 1. HANDLE GEMINI FUNCTION CALLS
                    # =====================================================

                    if response.tool_call:

                        print("\n================================")
                        print("GEMINI REQUESTED TOOL")
                        print("================================")

                        function_responses = []

                        for fc in response.tool_call.function_calls:

                            print("FUNCTION:", fc.name)
                            print("ARGS:", fc.args)

                            # ---------------------------------------------
                            # Knowledge Base Tool
                            # ---------------------------------------------

                            if fc.name == "search_knowledge_base":

                                query = fc.args.get("query", "")

                                print("\nRAW TOOL QUERY:", query)

                                print("CONVERSATION HISTORY:")
                                for item in conversation_history[-12:]:
                                    print("   ", item)

                                resolved_query = await resolve_contextual_query(
                                    query,
                                    conversation_history
                                )

                                print("CONTEXT RESOLVED QUERY:", resolved_query)

                                print("FINAL SEARCH QUERY:", resolved_query)

                                result = await search_knowledge_base_tool(
                                    resolved_query,
                                )

                                function_responses.append(
                                    types.FunctionResponse(
                                        name=fc.name,
                                        id=fc.id,
                                        response={
                                            "result": result
                                        }
                                    )
                                )

                                # Send debugging information to frontend
                                await websocket.send_json({
                                    "type": "tool_call",
                                    "tool": fc.name,
                                    "query": resolved_query
                                })

                            # ---------------------------------------------
                            # Structured Government Scheme Tool
                            # ---------------------------------------------

                            elif fc.name == "get_government_scheme":

                                scheme_id = fc.args.get("scheme_id", "")

                                print("\n==============================")
                                print("STRUCTURED SCHEME TOOL CALLED")
                                print("SCHEME ID:", scheme_id)
                                print("==============================")

                                result = await get_government_scheme(
                                    scheme_id
                                )

                                function_responses.append(
                                    types.FunctionResponse(
                                        name=fc.name,
                                        id=fc.id,
                                        response={
                                            "result": result
                                        }
                                    )
                                )

                                # Send debugging information to frontend
                                await websocket.send_json({
                                    "type": "tool_call",
                                    "tool": fc.name,
                                    "scheme_id": scheme_id
                                })

                            else:

                                print("UNKNOWN TOOL:", fc.name)

                                function_responses.append(
                                    types.FunctionResponse(
                                        name=fc.name,
                                        id=fc.id,
                                        response={
                                            "error": f"Unknown tool: {fc.name}"
                                        }
                                    )
                                )

                        # Send tool result back to Gemini
                        if function_responses:

                            print("SENDING TOOL RESPONSE TO GEMINI")

                            await session.send_tool_response(
                                function_responses=function_responses
                            )

                        # Tool call has been handled
                        continue


                    # =====================================================
                    # 2. HANDLE NORMAL GEMINI SERVER CONTENT
                    # =====================================================

                    if response.server_content:

                        # ---------------------------------------------
                        # User speech transcription
                        # ---------------------------------------------

                        if response.server_content.input_transcription:

                            text = response.server_content.input_transcription.text

                            if text:

                                print("User:", text)

                                conversation_history.append(
                                f"User: {text}"
                                )

                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": text
                                })


                        # ---------------------------------------------
                        # Gemini output transcription
                        # ---------------------------------------------

                        if response.server_content.output_transcription:

                            text = response.server_content.output_transcription.text

                            if text:

                                print("Gemini:", text)

                                conversation_history.append(
                                f"Samarth: {text}"
                            )

                                await websocket.send_json({
                                    "type": "assistant_transcript",
                                    "text": text
                                })


                        # ---------------------------------------------
                        # Gemini audio response
                        # ---------------------------------------------

                        if response.server_content.model_turn:

                            for part in response.server_content.model_turn.parts:

                                if part.inline_data:

                                    audio_data = part.inline_data.data

                                    await websocket.send_bytes(
                                        audio_data
                                    )

                                    print(
                                        "Sent Gemini audio:",
                                        len(audio_data),
                                        "bytes"
                                    )
                print("GEMINI RECEIVE LOOP ENDED")                    

            # Keep receiving Gemini responses
            gemini_task = asyncio.create_task(
                receive_from_gemini()
            )

            def gemini_task_done(task):
                if task.cancelled():
                    print("GEMINI RECEIVE TASK WAS CANCELLED")
                elif task.exception():
                    print("GEMINI RECEIVE TASK CRASHED:", repr(task.exception()))
                else:
                    print("GEMINI RECEIVE TASK FINISHED UNEXPECTEDLY")

            gemini_task.add_done_callback(gemini_task_done)

            try:

                while True:
                    message = await websocket.receive()

                    print("GEMINI TASK STATE:", gemini_task.done())

                    # Parse JSON messages from browser
                    if message.get("text"):
                        try:
                            message.update(json.loads(message["text"]))
                        except json.JSONDecodeError:
                            pass

                    print("BACKEND MESSAGE:", message)

                    # User started speaking
                    if message.get("activity_start"):
                        print("User started speaking.")

                        await session.send_realtime_input(
                            activity_start=types.ActivityStart()
                        )

                        print("Sent activity_start to Gemini.")

                    # Browser microphone audio
                    elif message.get("bytes"):
                        audio_data = message["bytes"]

                        print(
                            "Received microphone audio:",
                            len(audio_data),
                            "bytes"
                        )

                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=audio_data,
                                mime_type="audio/pcm;rate=16000"
                            )
                        )

                    # Browser finished speaking
                    elif message.get("audio_end"):
                        print("User stopped speaking.")

                        await session.send_realtime_input(
                            activity_end=types.ActivityEnd()
                        )

                        print("Sent activity_end to Gemini.")

                    # Browser text
                    elif message.get("text"):

                        text = message["text"]

                        print("Received text:", text)

                        await session.send_realtime_input(
                            text=text
                        )

            finally:

                gemini_task.cancel()

    except Exception as e:

        print("Voice connection error:", e)

        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass

    finally:

        print("Browser disconnected from /ws/voice")