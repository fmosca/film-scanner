import os
import vcr

# Get the absolute path to the fixtures directory within the tests folder
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

# Ensure the fixtures directory exists
os.makedirs(FIXTURE_DIR, exist_ok=True)

my_vcr = vcr.VCR(
    cassette_library_dir=FIXTURE_DIR,
    record_mode='once',
    filter_headers=['authorization', 'cookie'],
    filter_query_parameters=['api_key', 'token'],
    serializer='yaml',
)