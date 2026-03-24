from setuptools import setup

files = ["templates/models_logging/*", "migrations/*", "management/commands/*"]

setup(
    name="django-models-logging",
    version="5.2.0",
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
        "django>=5.2,<6.0",
        "python-dateutil",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 5.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    long_description="https://github.com/legion-an/django-models-logging/blob/master/README.md",
)
