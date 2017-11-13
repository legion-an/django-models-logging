from setuptools import setup

files = ["templates/models_logging/*", "migrations/*"]

setup(
    name='django-models-logging',
    version='0.9.2',
    packages=['models_logging'],
    url='https://bitbucket.org/legion_an/django-models-logging',
    package_data = {'models_logging' : files},
    license='',
    author='legion',
    author_email='legion.andrey.89@gmail.com',
    description='Add logging of models from save, delete signals',
    keywords=[
        'django logging',
        'django history',
        'django logging models',
        'django history models',
    ],
    install_requires=[
        "django",
    ],
)
