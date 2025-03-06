import vcr

my_vcr = vcr.VCR(
    cassette_library_dir='fixtures',
    path_transformer=vcr.VCR.ensure_suffix('.yaml'),
    record_mode='once',
)