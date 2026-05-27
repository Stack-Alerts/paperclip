#!/usr/bin/env python3
"""Test fabrication detector against historical cases.

Historical cases:
- BTCAAAAA-29368: fabricated "verified" closure with empty git diff and ~65-line offsets
- BTCAAAAA-29415: closed done with SHA not on main (existed on feature branch only)
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.closure_gate_routine import (
    sha_exists,
    get_commit_author,
    extract_file_line_references,
    validate_file_line_references,
)


def test_sha_existence():
    """Test SHA existence detection."""
    print("\n=== Testing SHA Existence Detection ===")

    # Real commit on main
    real_sha = "88599cd2b"  # BTCAAAAA-29368
    assert sha_exists(real_sha), f"SHA {real_sha} should exist"
    print(f"✓ Real SHA {real_sha} correctly identified as existing")

    # Another real commit
    real_sha2 = "3cbc56983"  # BTCAAAAA-29415
    assert sha_exists(real_sha2), f"SHA {real_sha2} should exist"
    print(f"✓ Real SHA {real_sha2} correctly identified as existing")

    # Fake/fabricated SHA
    fake_sha = "0000000000000000000000000000000000000000"
    assert not sha_exists(fake_sha), f"Fake SHA {fake_sha} should not exist"
    print(f"✓ Fake SHA {fake_sha} correctly identified as non-existent")


def test_author_extraction():
    """Test author extraction from commits."""
    print("\n=== Testing Author Extraction ===")

    # Real commit
    real_sha = "88599cd2b"
    author = get_commit_author(real_sha)
    assert author is not None, f"Should extract author for SHA {real_sha}"
    name, email = author
    print(f"✓ Extracted author from {real_sha}: {name} <{email}>")

    # Fake SHA should return None
    fake_sha = "0000000000000000000000000000000000000000"
    author = get_commit_author(fake_sha)
    assert author is None, f"Fake SHA {fake_sha} should return None"
    print(f"✓ Fake SHA {fake_sha} correctly returns None")


def test_file_line_extraction():
    """Test file:line reference extraction."""
    print("\n=== Testing File:Line Reference Extraction ===")

    # Test case 1: Single line reference
    text1 = "Fixed issue in packages/web-ui/app.tsx:594"
    refs1 = extract_file_line_references(text1)
    assert len(refs1) == 1, f"Should extract 1 reference, got {len(refs1)}"
    assert refs1[0] == ("packages/web-ui/app.tsx", 594, 594), f"Incorrect parse: {refs1[0]}"
    print(f"✓ Extracted single line reference: {refs1[0]}")

    # Test case 2: Line range reference
    text2 = "Updated packages/web-ui/components/Modal.tsx:100-150"
    refs2 = extract_file_line_references(text2)
    assert len(refs2) == 1, f"Should extract 1 reference, got {len(refs2)}"
    assert refs2[0] == ("packages/web-ui/components/Modal.tsx", 100, 150), f"Incorrect parse: {refs2[0]}"
    print(f"✓ Extracted line range reference: {refs2[0]}")

    # Test case 3: Multiple references
    text3 = "Changed src/utils/helper.py:42 and src/main.py:10-15"
    refs3 = extract_file_line_references(text3)
    assert len(refs3) == 2, f"Should extract 2 references, got {len(refs3)}"
    print(f"✓ Extracted {len(refs3)} references from text with multiple files")

    # Test case 4: No references
    text4 = "This is just plain text with no file references"
    refs4 = extract_file_line_references(text4)
    assert len(refs4) == 0, f"Should extract 0 references, got {len(refs4)}"
    print(f"✓ Correctly extracted 0 references from plain text")


def test_line_validation():
    """Test file:line validation against actual commits."""
    print("\n=== Testing File:Line Validation ===")

    # Real commit with real file
    sha = "88599cd2b"
    refs = [("packages/web-ui/app/strategy-builder/page.tsx", 1, 50)]

    errors = validate_file_line_references(refs, sha)
    if errors:
        print(f"✗ Validation errors (file may have changed): {errors}")
    else:
        print(f"✓ Valid file:line reference at SHA {sha}")

    # Fake line range (beyond EOF)
    refs_bad = [("packages/web-ui/app/strategy-builder/page.tsx", 99999, 99999)]
    errors_bad = validate_file_line_references(refs_bad, sha)
    assert len(errors_bad) > 0, "Should detect out-of-range line numbers"
    print(f"✓ Correctly detected out-of-range line reference: {errors_bad[0][1]}")


def test_historical_cases():
    """Test against documented historical fabrication cases."""
    print("\n=== Testing Historical Fabrication Cases ===")

    # BTCAAAAA-29368: fabricated closure with empty diff
    # The actual fix was committed as 88599cd2b
    sha_29368 = "88599cd2b"
    assert sha_exists(sha_29368), f"BTCAAAAA-29368 fix SHA {sha_29368} should exist"
    author = get_commit_author(sha_29368)
    assert author is not None, f"Should extract author for BTCAAAAA-29368 SHA"
    print(f"✓ BTCAAAAA-29368: SHA {sha_29368} exists with author {author[0]}")

    # BTCAAAAA-29415: closed done with SHA not on main
    # The commit 3cbc56983 existed but was on a feature branch, not main
    sha_29415 = "3cbc56983"
    assert sha_exists(sha_29415), f"BTCAAAAA-29415 SHA {sha_29415} should exist locally"
    # Note: The fabrication here was that it wasn't on origin/main, not that it didn't exist
    # That's caught by the ancestor check, not the existence check
    print(f"✓ BTCAAAAA-29415: SHA {sha_29415} exists (but wasn't on main - caught by ancestor check)")


if __name__ == "__main__":
    try:
        test_sha_existence()
        test_author_extraction()
        test_file_line_extraction()
        test_line_validation()
        test_historical_cases()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
