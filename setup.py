from setuptools import setup

files = ["templates/models_logging/*", "migrations/*", "management/commands/*"]

setup(
    name='django-models-logging',
    version='1.0.4',
    packages=['models_logging'],
    url='https://github.com/legion-an/django-models-logging',
    package_data = {'models_logging' : files},
    license='MIT',
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
        "django>=2.0",
        "python-dateutil",
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 3.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
