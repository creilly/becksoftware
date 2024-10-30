import hitran

if __name__ == '__main__':
    db = hitran.get_db(11)
    dbl = db.iloc[0]
    ulq = hitran.parse_lq(dbl['ulq'],hitran.NH3)
    htd = hitran.lookup_line(dbl['line'])
    print(
        db[
            db.apply(
                lambda x: hitran.parse_lq(x['llq'],hitran.NH3)[3]=='A1\'',
                axis=1
            )
        ]
    )