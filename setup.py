from setuptools import setup
from cmstransfer import __version__


setup(
    name='djangocms-content-transfer',
    version=__version__,
    author='InQuant GmbH',
    author_email='info@inquant.de',
    packages=['cmstransfer'],
    url='',
    license='MIT',
    description='Usefull to transfer Page-, PageContent-, Alias-, Placeholder-Objects from one CMS System to another.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    zip_safe=False,
    include_package_data=True,
    package_data={'': ['README.md'], },
    install_requires=['django-cms', 'djangocms_plus'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django CMS',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    extras_require={},
)
