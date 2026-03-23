from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="Support Agent API",
        description="Smart support agent for HelpScout, Facebook, and Phone support",
        version="1.0.0",
    )
    return app
