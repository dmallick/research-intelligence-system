import os

def create_project_structure():
    """
    Creates the project directory and file structure automatically.
    """
    structure = [
        #"research-intelligence-system/",
        "research-intelligence-system/agents/__init__.py",
        "research-intelligence-system/agents/base/__init__.py",
        "research-intelligence-system/agents/base/agent.py",
        "research-intelligence-system/agents/base/memory.py",
        "research-intelligence-system/agents/research/__init__.py",
        "research-intelligence-system/agents/research/research_agent.py",
        "research-intelligence-system/agents/fact_checker/__init__.py",
        "research-intelligence-system/agents/fact_checker/fact_checker_agent.py",
        "research-intelligence-system/agents/content_generator/__init__.py",
        "research-intelligence-system/agents/content_generator/content_agent.py",
        "research-intelligence-system/agents/qa/__init__.py",
        "research-intelligence-system/agents/qa/qa_agent.py",
        "research-intelligence-system/agents/orchestrator/__init__.py",
        "research-intelligence-system/agents/orchestrator/orchestrator_agent.py",
        "research-intelligence-system/api/__init__.py",
        "research-intelligence-system/api/main.py",
        "research-intelligence-system/api/routes/__init__.py",
        "research-intelligence-system/api/routes/research.py",
        "research-intelligence-system/api/routes/health.py",
        "research-intelligence-system/api/routes/agents.py",
        "research-intelligence-system/api/middleware/__init__.py",
        "research-intelligence-system/api/middleware/auth.py",
        "research-intelligence-system/api/middleware/rate_limit.py",
        "research-intelligence-system/core/__init__.py",
        "research-intelligence-system/core/config.py",
        "research-intelligence-system/core/database.py",
        "research-intelligence-system/core/vector_store.py",
        "research-intelligence-system/core/message_queue.py",
        "research-intelligence-system/models/__init__.py",
        "research-intelligence-system/models/research.py",
        "research-intelligence-system/models/content.py",
        "research-intelligence-system/models/agent_state.py",
        "research-intelligence-system/utils/__init__.py",
        "research-intelligence-system/utils/logging.py",
        "research-intelligence-system/utils/validators.py",
        "research-intelligence-system/utils/helpers.py",
        "research-intelligence-system/tests/__init__.py",
        "research-intelligence-system/tests/conftest.py",
        "research-intelligence-system/tests/unit/",
        "research-intelligence-system/tests/integration/",
        "research-intelligence-system/tests/fixtures/",
        "research-intelligence-system/docker/Dockerfile",
        "research-intelligence-system/docker/docker-compose.yml",
        "research-intelligence-system/docker/docker-compose.dev.yml",
        "research-intelligence-system/scripts/setup.py",
        "research-intelligence-system/scripts/migrate.py",
        "research-intelligence-system/scripts/seed.py",
        "research-intelligence-system/requirements/base.txt",
        "research-intelligence-system/requirements/dev.txt",
        "research-intelligence-system/requirements/prod.txt",
        "research-intelligence-system/.env.example",
        #"research-intelligence-system/.gitignore",
        "research-intelligence-system/pytest.ini",
        "research-intelligence-system/pyproject.toml"
        #"research-intelligence-system/README.md"
    ]

    for path in structure:
        if path.endswith('/'):
            # It's a directory
            os.makedirs(path, exist_ok=True)
            print(f"Created directory: {path}")
        else:
            # It's a file
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            open(path, 'a').close()
            print(f"Created file: {path}")

if __name__ == "__main__":
    create_project_structure()