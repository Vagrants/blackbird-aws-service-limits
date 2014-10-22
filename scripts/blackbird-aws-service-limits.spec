%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

%define name blackbird-aws-service-limits
%define version 0.1.1
%define unmangled_version %{version}
%define release 1%{dist}
%define include_dir /etc/blackbird/conf.d
%define plugins_dir /opt/blackbird/plugins

Summary: Blackbird plugin AWS Service limits.
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: WTFPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Vagrants <vagrants@gmail.com>
Packager: Vagrants <vagrants@gmail.com>
Requires: blackbird python-boto
Url: https://github.com/Vagrants/blackbird-aws-service-limits
BuildRequires:  python-setuptools

%description
UNKNOWN

%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

install -dm 0755 $RPM_BUILD_ROOT%{include_dir}
install -dm 0755 $RPM_BUILD_ROOT%{plugins_dir}
install -p -m 0644 scripts/aws-service-limits.cfg $RPM_BUILD_ROOT%{include_dir}/aws-service-limits.cfg
install -p -m 0644 aws_service_limits.py $RPM_BUILD_ROOT%{plugins_dir}/aws_service_limits.py

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%config(noreplace) %{include_dir}/aws-service-limits.cfg
%{plugins_dir}/aws_service_limits.*

%changelog
* Wed Oct 22 2014 Vagrants <vagrants@gmail.com> - 0.1.1-1
- Support DynamoDB capacity units
* Tue Oct 21 2014 Vagrants <vagrants@gmail.com> - 0.1.0-1
- Initial package
