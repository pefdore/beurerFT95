from setuptools import setup

setup(
    name="ft95",
    version="0.1.0",
    description="Affichage PC des températures du thermomètre Beurer FT95 (Bluetooth LE)",
    packages=["ft95"],
    install_requires=["bleak>=0.21.0"],
    python_requires=">=3.9",
    entry_points={"console_scripts": ["ft95=ft95.cli:main"]},
)
