import sampleheater

anneal_time_minutes = 5 # minutes
anneal_temp_kelvin = 800 # Kelvin

with sampleheater.SampleHeaterHandler() as shh:
    assert shh.get_process_value_unit() == sampleheater.KELVIN