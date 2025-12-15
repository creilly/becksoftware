import hitran

if __name__ == '__main__':    
    mol = hitran.CH4
    db = hitran.get_db(mol)
    dbl = db.iloc[0]
    ulq = hitran.parse_lq(dbl['ulq'],mol)
    htd = hitran.lookup_line(dbl['line'])    
    exit()
    print(
        db[
            db.apply(
                lambda x: x['iso'] == hitran.ISO_CH4,
                axis=1
            )
        ]
    )