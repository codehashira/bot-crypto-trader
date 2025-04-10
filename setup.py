from setuptools import setup, find_packages

setup(
    name="crypto_trading_bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.7.0",
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "ccxt>=2.0.0",
        "pydantic>=1.8.0",
        "matplotlib>=3.4.0",
        "python-telegram-bot>=13.0.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.18.0",
    ],
    python_requires=">=3.8",
)