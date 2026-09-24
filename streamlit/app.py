
import requests
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Resume Screening",
    page_icon="📄",
    layout="wide",
)


# ============================================================
# BASIC HELPERS
# ============================================================

def to_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def percentage_text(value):
    number = to_float(value)

    if number is None:
        return "N/A"

    if number <= 1:
        number *= 100

    return f"{number:.2f}%"


# ============================================================
# FLATTEN ACTUAL FASTAPI RESULT
# ============================================================

def flatten_actual_screening(
    screening,
    filename="Resume",
):
    """
    Handles the actual current FastAPI structure:

    screening = {
        "match_score": ...,
        "match_score_percent": ...,
        "pre_screen": {...},
        "positive_factors": [...],
        "review_flags": [...],
        "skills": {...},
        "experience": {...},
        "model_scores": {...},
        "cluster": ...,
        "candidate": {...},
        "job": {...}
    }
    """

    if not isinstance(screening, dict):
        return None

    pre_screen = screening.get(
        "pre_screen",
        {}
    )

    skills = screening.get(
        "skills",
        {}
    )

    experience = screening.get(
        "experience",
        {}
    )

    model_scores = screening.get(
        "model_scores",
        {}
    )

    candidate = screening.get(
        "candidate",
        {}
    )

    education = candidate.get(
        "education",
        []
    )

    if not isinstance(education, list):
        education = []

    match_percent = screening.get(
        "match_score_percent"
    )

    if match_percent is None:
        match_percent = screening.get(
            "match_score"
        )

    return {
        "resume_filename": (
            filename
            or candidate.get(
                "filename"
            )
            or "Resume"
        ),

        "match_score": match_percent,

        "pre_screen": pre_screen.get(
            "status",
            "N/A"
        ),

        "pre_screen_ready": pre_screen.get(
            "ready"
        ),

        "cluster": screening.get(
            "cluster",
            "N/A"
        ),

        "experience_score": model_scores.get(
            "experience_score"
        ),

        "candidate_experience_years": experience.get(
            "candidate_years"
        ),

        "candidate_experience_display": experience.get(
            "candidate_display"
        ),

        "required_experience_years": experience.get(
            "required_years"
        ),

        "required_experience_display": experience.get(
            "required_display"
        ),

        "matched_skills": skills.get(
            "matched",
            []
        ),

        "missing_skills": skills.get(
            "missing",
            []
        ),

        "education": education,

        "positive_factors": screening.get(
            "positive_factors",
            []
        ),

        "review_flags": screening.get(
            "review_flags",
            []
        ),

        "raw": screening,
    }


# ============================================================
# NORMALIZE BATCH RESPONSE
# ============================================================

def normalize_batch_response(data):
    """
    Handles the ACTUAL current /batch-screen response:

    {
        "results": [
            {
                "index": 0,
                "filename": "...",
                "status": "SUCCESS",
                "screening": {...}
            }
        ]
    }
    """

    if not isinstance(data, dict):
        return []

    api_results = data.get(
        "results",
        []
    )

    if not isinstance(
        api_results,
        list
    ):
        return []

    normalized = []

    for item in api_results:

        if not isinstance(item, dict):
            continue

        screening = item.get(
            "screening"
        )

        if not isinstance(
            screening,
            dict
        ):
            continue

        # Status is informative only.
        # We do not reject a result because of
        # SUCCESS/success capitalization.
        filename = (
            item.get("filename")
            or screening.get(
                "candidate",
                {}
            ).get(
                "filename"
            )
            or "Resume"
        )

        result = flatten_actual_screening(
            screening,
            filename=filename,
        )

        if result is not None:
            normalized.append(result)

    return normalized


# ============================================================
# NORMALIZE SINGLE RESPONSE
# ============================================================

def normalize_single_response(
    data,
    filename,
):
    """
    Supports both possible single-screen response styles:

    1. Direct screening object
    2. Wrapper containing screening
    """

    if not isinstance(
        data,
        dict
    ):
        return []

    # --------------------------------------------------------
    # Current-style wrapper
    # --------------------------------------------------------

    if isinstance(
        data.get("screening"),
        dict
    ):

        result = flatten_actual_screening(
            data["screening"],
            filename=filename,
        )

        return [result] if result else []

    # --------------------------------------------------------
    # Direct current-style response
    # --------------------------------------------------------

    if (
        "match_score" in data
        or "match_score_percent" in data
    ):

        result = flatten_actual_screening(
            data,
            filename=filename,
        )

        return [result] if result else []

    # --------------------------------------------------------
    # Older validated response style
    # --------------------------------------------------------

    if isinstance(
        data.get("match"),
        dict
    ):

        match = data.get(
            "match",
            {}
        )

        pre_screen = data.get(
            "pre_screen",
            {}
        )

        cluster = data.get(
            "cluster",
            {}
        )

        model = data.get(
            "model",
            {}
        )

        features = model.get(
            "features",
            {}
        )

        skills = pre_screen.get(
            "skills",
            {}
        )

        education = pre_screen.get(
            "education",
            {}
        )

        return [{
            "resume_filename": filename,
            "match_score": match.get(
                "percentage"
            ),
            "pre_screen": pre_screen.get(
                "overall",
                "N/A"
            ),
            "pre_screen_ready": None,
            "cluster": cluster.get(
                "cluster_id",
                "N/A"
            ),
            "experience_score": model.get(
                "experience_score"
            ),
            "candidate_experience_years": features.get(
                "candidate_experience_years"
            ),
            "candidate_experience_display": None,
            "required_experience_years": features.get(
                "required_experience_years"
            ),
            "required_experience_display": None,
            "matched_skills": skills.get(
                "matched",
                []
            ),
            "missing_skills": skills.get(
                "missing",
                []
            ),
            "education": education.get(
                "matched",
                []
            ),
            "positive_factors": match.get(
                "positive_factors",
                []
            ),
            "review_flags": match.get(
                "review_flags",
                []
            ),
            "raw": data,
        }]


    return []


# ============================================================
# FASTAPI SINGLE SCREEN
# ============================================================

def request_single_screen(
    api_url,
    uploaded_file,
    job_title,
    job_description,
    similar_top_k,
):
    response = requests.post(
        f"{api_url}/api/v1/screen",
        files={
            "resume": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type
                or "application/octet-stream",
            )
        },
        data={
            "job_description": job_description,
            "title": job_title,
            "similar_top_k": str(
                similar_top_k
            ),
        },
        timeout=300,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# FASTAPI BATCH SCREEN
# ============================================================

def request_batch_screen(
    api_url,
    uploaded_files,
    job_title,
    job_description,
):
    multipart_files = []

    for uploaded_file in uploaded_files:

        multipart_files.append(
            (
                "resumes",
                (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type
                    or "application/octet-stream",
                ),
            )
        )

    response = requests.post(
        f"{api_url}/api/v1/batch-screen",
        files=multipart_files,
        data={
            "job_description": job_description,
            "title": job_title,
        },
        timeout=600,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# HEADER
# ============================================================

st.title(
    "📄 AI Resume Screening"
)

st.caption(
    "Smart Candidate Matching with Machine Learning"
)

st.divider()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "Screening Settings"
    )

    api_url = st.text_input(
        "FastAPI URL",
        value="http://127.0.0.1:8000",
    ).strip().rstrip("/")

    similar_top_k = st.slider(
        "Similar resumes",
        min_value=1,
        max_value=10,
        value=5,
    )

    st.divider()

    st.info(
        """
**Backend:** FastAPI

**ML:** Random Forest

**Semantic Matching:** Sentence Transformers

**Similarity Search:** FAISS

**Clustering:** KMeans
"""
    )


# ============================================================
# JOB INFORMATION
# ============================================================

st.subheader(
    "Job Information"
)

job_title = st.text_input(
    "Job Title",
    value="Graphic Designer",
)

job_description = st.text_area(
    "Job Description",
    height=240,
    placeholder=(
        "Enter the complete job description "
        "including required skills, experience "
        "and education."
    ),
)


# ============================================================
# RESUME UPLOAD
# ============================================================

st.subheader(
    "Upload Resumes"
)

uploaded_files = st.file_uploader(
    "Upload one or more resumes",
    type=[
        "pdf",
        "docx",
        "txt",
    ],
    accept_multiple_files=True,
)

if uploaded_files:

    st.success(
        f"{len(uploaded_files)} resume(s) selected."
    )

    for index, uploaded_file in enumerate(
        uploaded_files,
        start=1,
    ):

        st.write(
            f"**{index}. {uploaded_file.name}** "
            f"({uploaded_file.size / 1024:.1f} KB)"
        )


# ============================================================
# SCREEN BUTTON
# ============================================================

screen_button = st.button(
    "🚀 Screen Resumes",
    type="primary",
    use_container_width=True,
)


# ============================================================
# PROCESS SCREENING
# ============================================================

if screen_button:

    if not job_description.strip():

        st.error(
            "Please enter the job description."
        )

        st.stop()

    if not uploaded_files:

        st.error(
            "Please upload at least one resume."
        )

        st.stop()

    # Clear old result.
    st.session_state[
        "screening_results"
    ] = []

    st.session_state[
        "raw_response"
    ] = None


    # ========================================================
    # SINGLE
    # ========================================================

    if len(uploaded_files) == 1:

        with st.spinner(
            "Screening resume..."
        ):

            try:

                raw_response = request_single_screen(
                    api_url,
                    uploaded_files[0],
                    job_title,
                    job_description,
                    similar_top_k,
                )

                results = normalize_single_response(
                    raw_response,
                    uploaded_files[0].name,
                )

                st.session_state[
                    "screening_results"
                ] = results

                st.session_state[
                    "raw_response"
                ] = raw_response

                if results:

                    st.success(
                        "Resume screening completed successfully."
                    )

                else:

                    st.error(
                        "The API returned a response, "
                        "but the result structure was not recognized."
                    )

            except requests.RequestException as exc:

                st.error(
                    f"FastAPI request failed: {exc}"
                )

                st.stop()

            except Exception as exc:

                st.error(
                    f"Unexpected error: {exc}"
                )

                st.stop()


    # ========================================================
    # BATCH
    # ========================================================

    else:

        with st.spinner(
            f"Screening {len(uploaded_files)} resumes..."
        ):

            try:

                raw_response = request_batch_screen(
                    api_url,
                    uploaded_files,
                    job_title,
                    job_description,
                )

                results = normalize_batch_response(
                    raw_response
                )

                st.session_state[
                    "screening_results"
                ] = results

                st.session_state[
                    "raw_response"
                ] = raw_response

                if results:

                    st.success(
                        f"{len(results)} resume(s) "
                        "processed successfully."
                    )

                else:

                    st.error(
                        "The batch request completed, "
                        "but no candidate results were found."
                    )

            except requests.RequestException as exc:

                st.error(
                    f"FastAPI batch request failed: {exc}"
                )

                st.stop()

            except Exception as exc:

                st.error(
                    f"Unexpected error: {exc}"
                )

                st.stop()


# ============================================================
# RESULTS
# ============================================================

results = st.session_state.get(
    "screening_results",
    []
)

raw_response = st.session_state.get(
    "raw_response"
)


if results:

    st.divider()

    st.header(
        f"Screening Results ({len(results)})"
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    scores = []

    for result in results:

        score = to_float(
            result.get(
                "match_score"
            )
        )

        if score is not None:

            if score <= 1:
                score *= 100

            scores.append(score)


    needs_review = sum(
        1
        for result in results
        if str(
            result.get(
                "pre_screen",
                ""
            )
        ).upper()
        == "NEEDS_REVIEW"
    )


    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Total Resumes",
            len(results)
        )

    with col2:

        if scores:

            st.metric(
                "Average Match Score",
                f"{sum(scores) / len(scores):.2f}%"
            )

        else:

            st.metric(
                "Average Match Score",
                "N/A"
            )

    with col3:

        st.metric(
            "Needs Review",
            needs_review
        )


    st.divider()


    # ========================================================
    # CANDIDATE CARDS
    # ========================================================

    for index, result in enumerate(
        results,
        start=1,
    ):

        filename = result.get(
            "resume_filename",
            f"Candidate {index}"
        )

        st.subheader(
            f"{index}. {filename}"
        )


        c1, c2, c3, c4 = st.columns(4)


        with c1:

            st.metric(
                "Match Score",
                percentage_text(
                    result.get(
                        "match_score"
                    )
                )
            )


        with c2:

            st.metric(
                "Pre-screen",
                str(
                    result.get(
                        "pre_screen",
                        "N/A"
                    )
                )
            )


        with c3:

            st.metric(
                "Cluster",
                str(
                    result.get(
                        "cluster",
                        "N/A"
                    )
                )
            )


        with c4:

            experience_score = result.get(
                "experience_score"
            )

            if experience_score is not None:

                st.metric(
                    "Experience Score",
                    f"{to_float(experience_score, 0):.2f}"
                )

            else:

                st.metric(
                    "Experience Score",
                    "N/A"
                )


        # ====================================================
        # EXPERIENCE
        # ====================================================

        exp1, exp2 = st.columns(2)


        with exp1:

            candidate_display = result.get(
                "candidate_experience_display"
            )

            candidate_years = result.get(
                "candidate_experience_years"
            )

            if candidate_display:

                st.write(
                    f"**Candidate Experience:** "
                    f"{candidate_display}"
                )

            elif candidate_years is not None:

                st.write(
                    f"**Candidate Experience:** "
                    f"{candidate_years:.2f} years"
                )

            else:

                st.write(
                    "**Candidate Experience:** "
                    "Not specified"
                )


        with exp2:

            required_display = result.get(
                "required_experience_display"
            )

            required_years = result.get(
                "required_experience_years"
            )

            if required_display:

                st.write(
                    f"**Required Experience:** "
                    f"{required_display}"
                )

            elif required_years is not None:

                st.write(
                    f"**Required Experience:** "
                    f"{required_years:.2f} years"
                )

            else:

                st.write(
                    "**Required Experience:** "
                    "Not specified"
                )


        # ====================================================
        # SKILLS
        # ====================================================

        skill1, skill2 = st.columns(2)


        with skill1:

            st.write(
                "**✅ Matched Required Skills**"
            )

            matched = result.get(
                "matched_skills",
                []
            )

            if matched:

                for skill in matched:

                    st.success(
                        str(skill),
                        icon="✅"
                    )

            else:

                st.caption(
                    "No required skills matched."
                )


        with skill2:

            st.write(
                "**❌ Missing Required Skills**"
            )

            missing = result.get(
                "missing_skills",
                []
            )

            if missing:

                for skill in missing:

                    st.error(
                        str(skill),
                        icon="❌"
                    )

            else:

                st.caption(
                    "No required skills missing."
                )


        # ====================================================
        # EDUCATION
        # ====================================================

        education = result.get(
            "education",
            []
        )

        st.write(
            "**🎓 Education**"
        )

        if education:

            st.write(
                ", ".join(
                    str(item)
                    for item in education
                )
            )

        else:

            st.caption(
                "No education information extracted."
            )


        # ====================================================
        # EXPLANATION
        # ====================================================

        with st.expander(
            "Model Explanation"
        ):

            positive = result.get(
                "positive_factors",
                []
            )

            flags = result.get(
                "review_flags",
                []
            )

            if positive:

                st.write(
                    "**Positive Factors**"
                )

                for factor in positive:

                    st.write(
                        f"• {factor}"
                    )


            if flags:

                st.write(
                    "**Review Flags**"
                )

                for flag in flags:

                    st.warning(
                        str(flag)
                    )


            if (
                not positive
                and not flags
            ):

                st.caption(
                    "No additional explanation available."
                )


        st.divider()


# ============================================================
# RAW API RESPONSE
# ============================================================

if raw_response:

    with st.expander(
        "🔎 Raw API Response"
    ):

        st.json(
            raw_response
        )


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "AI Resume Screening & Candidate Clustering"
)
