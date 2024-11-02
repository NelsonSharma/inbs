from setuptools import setup, find_packages

setup(
    name =                      'nbserver',
    version =                   '0.0.1',
    url =                       'https://github.com/NelsonSharma/nbserver',
    author =                    'Nelson.S',
    author_email =              'mail.nelsonsharma@gmail.com',
    description =               'Flask based notebook server',
    packages =                  find_packages(include=['nbserver']),
    classifiers=                ['License :: OSI Approved :: MIT License'],
    #package_dir =               { '' : ''},
    install_requires =          [],
    include_package_data =      False,
    #python_requires =           ">=3.8",
)   