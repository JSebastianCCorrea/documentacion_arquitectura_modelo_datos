from setuptools import setup

setup(
    name="arquitectura-modelo-datos-iudigital",
    version="1.0.0",
    description="Pipeline de ingesta, limpieza, enriquecimiento y modelo SQLite",
    author="Juan Sebastian Clavijo Correa",
    python_requires=">=3.12",
    py_modules=["enrichment", "cleaning", "ingestion", "model", "pipeline"],
    package_dir={"": "src"},
    install_requires=[
        "pandas==2.3.3", "numpy==1.26.4", "duckdb==1.5.5",
        "openpyxl==3.1.5", "lxml==5.3.2", "tzdata==2025.2",
    ],
    entry_points={"console_scripts": ["enriquecer-datos=enrichment:main", "integrar-datos=pipeline:main"]},
)
