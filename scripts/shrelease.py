import sampleheater

with sampleheater.SampleHeaterHandler() as shs:
    shs.release_control()