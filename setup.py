from setuptools import setup

files = ["templates/models_logging/*", "migrations/*", "management/commands/*"]

setup(
    name="django-models-logging",
    version="3.1.1",
    packages=["models_logging"],
    url="https://github.com/legion-an/django-models-logging",
    package_data={"models_logging": files},
    license="MIT",
    author="legion",
    author_email="legion.andrey.89@gmail.com",
    description="Add logging of models from save, delete signals",
    keywords=[
        "django logging",
        "django history",
        "django logging models",
        "django history models",
    ],
    install_requires=[
        "django>=3.1,<4.2",
        "python-dateutil",
    ],
    python_requires=">=3.8,<3.12",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 3.1",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    long_description="https://github.com/legion-an/django-models-logging/blob/master/README.md",
)
