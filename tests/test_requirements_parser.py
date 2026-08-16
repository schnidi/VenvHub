import sys
import os
import unittest
import pytest

# Pridanie koreňového adresára projektu do Python vyhľadávacej cesty
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import tempfile
import pytest
from core.logic.sluzby.requirements_parser import RequirementsParser


# 1. TEST PARSOVANIA #egg= (Bug #1 - napr. python-3parclient)
def test_extract_package_name_egg_variants():
    assert RequirementsParser._extract_package_name("git+https://github.com/user/repo.git#egg=requests") == "requests"
    assert RequirementsParser._extract_package_name("git+https://github.com/user/repo.git#egg=foo-bar") == "foo-bar"

    # Názvy s pomlčkou a číslicou (nie verzia)
    assert RequirementsParser._extract_package_name("git+https://github.com/user/repo.git#egg=python-3parclient") == "python-3parclient"
    assert RequirementsParser._extract_package_name("git+https://github.com/user/repo.git#egg=sec-101-tool") == "sec-101-tool"

    # Verzie cez '==' alebo legacy pomlčku
    assert RequirementsParser._extract_package_name("git+https://github.com/user/repo.git#egg=requests==2.25.1") == "requests"
    assert RequirementsParser._extract_package_name("git+https://github.com/user/repo.git#egg=my-pkg-1.2.3") == "my-pkg"


# 2. TEST PRIAMYCH REFERENCIÍ package@url (Bug #2)
def test_extract_package_name_direct_references():
    assert RequirementsParser._extract_package_name("requests @ https://github.com/psf/requests/archive/main.zip") == "requests"
    assert RequirementsParser._extract_package_name("requests@https://github.com/psf/requests/archive/main.zip") == "requests"
    assert RequirementsParser._extract_package_name("package-name@git+https://github.com/user/repo.git") == "package-name"
    assert RequirementsParser._extract_package_name("git@github.com:user/repo.git#egg=ssh-pkg") == "ssh-pkg"


# 3. TEST BEZPEČNOSTI PATH TRAVERSAL (Bug #3 - pokus o únik z adresára)
def test_path_traversal_protection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = os.path.join(tmp_dir, "project")
        os.makedirs(project_dir)
        
        # Tajný súbor MIMO projektu
        secret_file = os.path.join(tmp_dir, "secret.txt")
        with open(secret_file, "w") as f:
            f.write("secret-package==1.0.0\n")

        # Škodlivý requirements.txt
        malicious_req = os.path.join(project_dir, "requirements.txt")
        with open(malicious_req, "w") as f:
            f.write("-r ../secret.txt\n")
            f.write("valid-package==2.0.0\n")

        packages = RequirementsParser.parse(malicious_req)

        assert "valid-package" in packages
        assert "secret-package" not in packages  # Nesmie načítať zakázaný súbor!


# 4. TEST SPRACOVANIA KOMENTÁROV (Bug #4 - zakomentovaný #egg=)
def test_comment_with_egg_parsing():
    with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.txt') as f:
        f.write("# git+https://github.com/user/repo.git#egg=disabled-pkg\n")
        f.write("git+https://github.com/user/repo.git#egg=active-pkg # komentar\n")
        f.write("requests>=2.25.1 # komentar s #egg=ignored-pkg\n")
        f_path = f.name

    try:
        packages = RequirementsParser.parse(f_path)

        assert "active-pkg" in packages
        assert "requests" in packages
        assert "disabled-pkg" not in packages
        assert "ignored-pkg" not in packages
    finally:
        os.remove(f_path)


# 5. TEST NORMALIZÁCIE A DĹŽKY NÁZVU (Bug #5)
def test_normalize_length_limit():
    assert RequirementsParser._normalize("my-package") == "my-package"
    
    # Dlhý názov (250 znakov) musí prejsť
    long_name = "a" * 250
    assert RequirementsParser._normalize(long_name) == "a" * 250

    # Príliš dlhý názov (nad 1000 znakov) musí vrátiť prázdny reťazec
    too_long_name = "a" * 1001
    assert RequirementsParser._normalize(too_long_name) == ""

# Relatívne cesty na Windows / Linux bez prefixu ./ alebo .\
    assert RequirementsParser._extract_package_name("mypackage @ vendor/package.whl") == "mypackage"
    assert RequirementsParser._extract_package_name("mypackage @ wheels\\package-1.0.whl") == "mypackage"
    assert RequirementsParser._extract_package_name("mypackage@subfolder/deps/pkg.tar.gz") == "mypackage"

def test_requirement_flag_strict_parsing():
    with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.txt') as f:
        # Tieto musia prejsť:
        f.write("-r valid1.txt\n")
        f.write("-r=valid2.txt\n")
        f.write("--requirement valid3.txt\n")
        f.write("--requirement=valid4.txt\n")
        f.write("-r./valid5.txt\n")
        
        # Tieto sa NESMÚ vyhodnotiť ako -r súbor:
        f.write("-rinvalid.txt\n")  # Chýba medzera aj lomítko
        f_path = f.name

    # Vytvoríme pomocné validné súbory, aby ich parse našiel
    base_dir = os.path.dirname(f_path)
    for name in ["valid1.txt", "valid2.txt", "valid3.txt", "valid4.txt", "valid5.txt"]:
        with open(os.path.join(base_dir, name), "w") as vf:
            vf.write(f"pkg-{name.split('.')[0]}==1.0\n")

    try:
        packages = RequirementsParser.parse(f_path)
        assert len(packages) == 5
    finally:
        os.remove(f_path)
        for name in ["valid1.txt", "valid2.txt", "valid3.txt", "valid4.txt", "valid5.txt"]:
            p = os.path.join(base_dir, name)
            if os.path.exists(p):
                os.remove(p)

def test_symlink_path_traversal_protection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = os.path.join(tmp_dir, "project")
        outside_dir = os.path.join(tmp_dir, "outside")
        os.makedirs(project_dir)
        os.makedirs(outside_dir)

        # Súbor mimo projektu
        secret_file = os.path.join(outside_dir, "secret.txt")
        with open(secret_file, "w") as f:
            f.write("secret-pkg==1.0.0\n")

        # Symlink vo vnútri projektu ukazujúci mimo neho
        symlink_req = os.path.join(project_dir, "requirements.txt")
        
        try:
            os.symlink(secret_file, symlink_req)
        except (OSError, NotImplementedError):
            # Ak OS / používateľ nemá práva na symlinky na Win, test preskočíme
            pytest.skip("Symlinky nie sú podporované alebo chýbajú právomoci.")

        packages = RequirementsParser.parse(symlink_req)

        # Keďže symlink smeroval mimo základný adresár projektu, súbor sa nesmie načítať
        assert "secret-pkg" not in packages


class TestRequirementsParser(unittest.TestCase):

    def test_vcs_url_with_user_credentials(self):
        """Testuje správne parsovanie VCS URL obsahujúcej '@' v prihlasovacích údajoch."""
        token = "git+https://user@github.com/user/repo.git#egg=my-pkg"
        pkg_name = RequirementsParser._extract_package_name(token)
        assert pkg_name == "my-pkg"

    def test_pep508_direct_reference_with_at(self):
        """Testuje, že PEP 508 syntax (pkg @ url) zostala funkčná."""
        token = "foo-bar @ https://example.com/foo-bar.whl"
        pkg_name = RequirementsParser._extract_package_name(token)
        assert pkg_name == "foo-bar"

    def test_extract_package_name_from_egg_fragment_with_versions(self):
        """Testuje extrakciu názvu balíčka z #egg= fragmentu s rôznymi formátmi verzií."""
        cases = [
            ("git+https://github.com/user/repo.git#egg=Package-0.1-beta", "Package"),
            ("https://example.com/mod.tar.gz#egg=my-pkg-1.2.3", "my-pkg"),
            ("https://example.com/mod.tar.gz#egg=my_app-v2.0.0.dev1", "my_app"),
            ("https://example.com/mod.tar.gz#egg=simple-pkg", "simple-pkg"),
        ]
        for token, expected in cases:
            pkg_name = RequirementsParser._extract_package_name(token)
            assert pkg_name == expected


if __name__ == "__main__":
    unittest.main()


def test_continuation_lines_with_comments(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text(
        "requests \\ # inline komentár za lomítkom\n"
        "  >=2.25.0\n"
        "flask \\\n"
        "# celoriadkový komentár v strede pokračovania\n"
        "  ==2.0.1\n"
        "urllib3#nie_je_inline_komentar_ale_sucast_alebo_invalid\n"
    )

    packages = RequirementsParser.parse(str(req_file))

    assert "requests" in packages
    assert "flask" in packages


def test_path_traversal_and_case_insensitivity(tmp_path):
    # Vytvorenie adresárovej štruktúry
    base_dir = tmp_path / "app"
    base_dir.mkdir()
    
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    # Súbor mimo povoleného adresára
    outside_req = outside_dir / "forbidden.txt"
    outside_req.write_text("malicious-pkg\n")

    # Povolený vnorený súbor
    nested_req = base_dir / "nested.txt"
    nested_req.write_text("safe-pkg\n")

    # Hlavný súbor
    main_req = base_dir / "requirements.txt"
    main_req.write_text(
        f"-r {nested_req.name}\n"
        f"-r ../outside/forbidden.txt\n"
    )

    packages = RequirementsParser.parse(str(main_req))

    # safe-pkg musí byť načítaný, malicious-pkg musí byť zablokovaný
    assert "safe-pkg" in packages
    assert "malicious-pkg" not in packages


def test_requirements_parse_pip_e_root(tmp_path):
    # 1. Vytvorenie simulovaného pip-e root priečinka
    pip_e_root = tmp_path / "pip_e_packages"
    pip_e_root.mkdir()

    # 2. Vytvorenie balíčka 'moj-test-balicek' vo vnútri pip_e_root
    pkg_dir = pip_e_root / "moj_test_balicek"
    pkg_dir.mkdir()
    
    pyproject_file = pkg_dir / "pyproject.toml"
    pyproject_file.write_text(
        '[build-system]\n'
        'requires = ["setuptools>=61.0"]\n'
        'build-backend = "setuptools.build_meta"\n\n'
        '[project]\n'
        'name = "moj-test-balicek"\n'
        'version = "0.1.0"\n',
        encoding="utf-8"
    )

    # 3. Vytvorenie requirements.txt súboru odkazuijúceho na -e moj_test_balicek
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("-e moj_test_balicek\nrequests>=2.25.0\n", encoding="utf-8")

    # 4. Parsovanie s uvádzaním pip_e_root
    parsed_packages = RequirementsParser.parse(str(req_file), pip_e_root=str(pip_e_root))

    # 5. Overenie, že sa správne extrahoval názov balíčka z pyproject.toml v pip_e_root
    assert "moj-test-balicek" in parsed_packages
    assert "requests" in parsed_packages
