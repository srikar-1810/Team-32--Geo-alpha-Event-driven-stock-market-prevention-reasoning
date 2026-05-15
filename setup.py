from setuptools import find_packages, setup

setup(
    name="geomarketgpt",
    version="0.1.0",
    description="Generative Geopolitical Financial Intelligence System",
    author="GeoMarketGPT Team",
    packages=find_packages(include=["app", "app.*", "frontend", "frontend.*"]),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "httpx>=0.26.0",
            "mypy>=1.7.0",
            "ruff>=0.1.0",
        ],
    },
)
