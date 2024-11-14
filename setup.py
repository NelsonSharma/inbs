from setuptools import setup, find_packages

setup(
    name =                      'inbs',
    version =                   '0.0.3',
    url =                       'https://github.com/NelsonSharma/inbs',
    author =                    'Nelson.S',
    author_email =              'mail.nelsonsharma@gmail.com',
    description =               'Flask based notebook server',
    packages =                  find_packages(include=['inbs']),
    classifiers=                ['License :: OSI Approved :: MIT License'],
    #package_dir =               { '' : ''},
    install_requires =          [],
    include_package_data =      False,
    #python_requires =           ">=3.8",
)   