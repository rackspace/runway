"""Tests for runway.cfngin.lookups."""
import unittest

from runway.cfngin.lookups import extract_lookups, extract_lookups_from_string


class TestLookupExtraction(unittest.TestCase):
    """Tests for runway.cfngin.lookups."""

    def test_no_lookups(self):
        """Test no lookups."""
        lookups = extract_lookups("value")
        self.assertEqual(lookups, set())

    def test_single_lookup_string(self):
        """Test single lookup string."""
        lookups = extract_lookups("${output fakeStack::FakeOutput}")
        self.assertEqual(len(lookups), 1)

    def test_multiple_lookups_string(self):
        """Test multiple lookups string."""
        lookups = extract_lookups(
            "url://${output fakeStack::FakeOutput}@"
            "${output fakeStack::FakeOutput2}"
        )
        self.assertEqual(len(lookups), 2)
        self.assertEqual(list(lookups)[0].type, "output")

    def test_lookups_list(self):
        """Test lookups list."""
        lookups = extract_lookups([
            "something",
            "${output fakeStack::FakeOutput}"
        ])
        self.assertEqual(len(lookups), 1)

    def test_lookups_dict(self):
        """Test lookups dict."""
        lookups = extract_lookups({
            "something": "${output fakeStack::FakeOutput}",
            "other": "value",
        })
        self.assertEqual(len(lookups), 1)

    def test_lookups_mixed(self):
        """Test lookups mixed."""
        lookups = extract_lookups({
            "something": "${output fakeStack::FakeOutput}",
            "list": ["value", "${output fakeStack::FakeOutput2}"],
            "dict": {
                "other": "value",
                "another": "${output fakeStack::FakeOutput3}",
            },
        })
        self.assertEqual(len(lookups), 3)

    def test_nested_lookups_string(self):
        """Test nested lookups string."""
        lookups = extract_lookups(
            "${noop ${output stack::Output},${output stack::Output2}}"
        )
        self.assertEqual(len(lookups), 2)

    def test_comma_delimited(self):
        """Test comma delimited."""
        lookups = extract_lookups("${noop val1,val2}")
        self.assertEqual(len(lookups), 1)

    def test_kms_lookup(self):
        """Test kms lookup."""
        query = ('CiADsGxJp1mCR21fjsVjVxr7RwuO2FE3ZJqC4iG0Lm+HkRKwAQEBAgB4A7Bs'
                 'SadZgkdtX47FY1ca+0cLjthRN2SaguIhtC5vh5EAAACHMIGEBgkqhkiG9w0B'
                 'BwagdzB1AgEAMHAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQM3IKyEoNE'
                 'QVxN3BaaAgEQgEOpqa0rcl3WpHOmblAqL1rOPRyokO3YXcJAAB37h/WKLpZZ'
                 'RAWV2h9C67xjlsj3ebg+QIU91T/')
        lookups = extract_lookups('${kms %s}' % query)
        self.assertEqual(len(lookups), 1)
        lookup = list(lookups)[0]
        self.assertEqual(lookup.type, 'kms')
        self.assertEqual(lookup.input, query)

    def test_kms_lookup_with_equals(self):
        """Test kms lookup with equals."""
        query = ('us-east-1@AQECAHjLp186mZ+mgXTQSytth/ibiIdwBm8CZAzZNSaSkSRqsw'
                 'AAAG4wbAYJKoZIhvcNAQcGoF8wXQIBADBYBgkqhkiG9w0BBwEwHgYJYIZIAW'
                 'UDBAEuMBEEDLNmhGU6fe4vp175MAIBEIAr+8tUpi7SDzOZm+FFyYvWXhs4hE'
                 'EyaazIn2dP8a+yHzZYDSVYGRpfUz34bQ==')
        lookups = extract_lookups('${kms %s}' % query)
        self.assertEqual(len(lookups), 1)
        lookup = list(lookups)[0]
        self.assertEqual(lookup.type, 'kms')
        self.assertEqual(lookup.input, query)

    def test_kms_lookup_with_region(self):
        """Test kms lookup with region."""
        query = ('us-west-2@CiADsGxJp1mCR21fjsVjVxr7RwuO2FE3ZJqC4iG0Lm+HkRKwAQ'
                 'EBAgB4A7BsSadZgkdtX47FY1ca+0cLjthRN2SaguIhtC5vh5EAAACHMIGEBg'
                 'kqhkiG9w0BBwagdzB1AgEAMHAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQ'
                 'QM3IKyEoNEQVxN3BaaAgEQgEOpqa0rcl3WpHOmblAqL1rOPRyokO3YXcJAAB'
                 '37h/WKLpZZRAWV2h9C67xjlsj3ebg+QIU91T/')
        lookups = extract_lookups('${kms %s}' % query)
        self.assertEqual(len(lookups), 1)
        lookup = list(lookups)[0]
        self.assertEqual(lookup.type, 'kms')
        self.assertEqual(lookup.input, query)

    def test_kms_file_lookup(self):
        """Test kms file lookup."""
        lookups = extract_lookups("${kms file://path/to/some/file.txt}")
        self.assertEqual(len(lookups), 1)
        lookup = list(lookups)[0]
        self.assertEqual(lookup.type, "kms")
        self.assertEqual(lookup.input, "file://path/to/some/file.txt")

    def test_valid_extract_lookups_from_string(self):
        """Test valid extract lookups from string."""
        _type = "output"
        _input = "vpc::PublicSubnets"
        value = "${%s %s}" % (_type, _input)
        lookups = extract_lookups_from_string(value)
        lookup = lookups.pop()
        assert lookup.type == _type
        assert lookup.input == _input
        assert lookup.raw == "%s %s" % (_type, _input)
