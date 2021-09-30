from datetime import date
import setuptools
setuptools.setup(
    name="breadcrumbsaddressbar",
    version="{d.year}.{d.month}{d.day:02}".format(d=date.today())[2:],
    packages=["breadcrumbsaddressbar"],
)
