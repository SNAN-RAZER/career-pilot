from app.models.job import JobPosting


class JobPreFilter:

    REJECTED_TITLE_TERMS = [
        "research scientist",
        "research engineer",
        "researcher",
        "data scientist",
        "data analyst",
        "data engineer",
        "business analyst",
        "qa engineer",
        "test engineer",
        "network engineer",
        "devops engineer",
        "software support",
        "technical support",
        "sales",
    ]

    AI_TITLE_TERMS = [
        "ai engineer",
        "artificial intelligence engineer",
        "ai developer",
        "artificial intelligence developer",
        "gen ai",
        "genai",
        "generative ai",
        "agentic ai",
        "llm engineer",
        "llm developer",
        "rag engineer",
        "rag specialist",
        "machine learning engineer",
        "ml engineer",
        "ai/ml engineer",
    ]

    AI_DESCRIPTION_TERMS = [
        "large language model",
        "llm",
        "retrieval augmented generation",
        "rag",
        "generative ai",
        "agentic ai",
        "langchain",
        "vector database",
        "vector search",
        "embeddings",
        "artificial intelligence",
    ]

    def match(
        self,
        job: JobPosting,
    ) -> bool:

        title = job.title.lower()

        description = (
            job.description or ""
        ).lower()

        # -----------------------------------------
        # 1. Reject clearly unrelated title
        # -----------------------------------------

        for term in self.REJECTED_TITLE_TERMS:

            if term in title:
                return False

        # -----------------------------------------
        # 2. Strong AI title
        # -----------------------------------------

        for term in self.AI_TITLE_TERMS:

            if term in title:
                return True

        # -----------------------------------------
        # 3. AI-related description
        #
        # Allows things such as:
        # "Software Engineer - GenAI"
        # "Engineering Document Intelligence"
        # -----------------------------------------

        ai_signals = 0

        for term in self.AI_DESCRIPTION_TERMS:

            if term in description:
                ai_signals += 1

        return ai_signals >= 2