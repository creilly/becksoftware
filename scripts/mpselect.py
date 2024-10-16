import multiplexer, lockin, argparse

A, B, C, D = 'a', 'b', 'c', 'd'

mpd = {
    A:multiplexer.A,
    B:multiplexer.B,
    C:multiplexer.C,
    D:multiplexer.D
}
ap = argparse.ArgumentParser(description='set multiplexer output')

ap.add_argument('channel',choices=sorted(mpd.keys()))

channel = mpd[ap.parse_args().channel]

with lockin.LockinHandler() as lih:
    multiplexer.set_output(lih,channel)