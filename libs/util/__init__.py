# prints in scientific notation with units (y.yyy x 10^z unit^{a/b} ... )
def fmt_num(f,digits,*units,sign_man=False,sign_exp=False):    
    def parse_sign(sign,filter):
        return {
            '-':'-',
            '+':{
                True:'+',
                False:''
            }[filter]
        }[sign]    
    mpair, epair = [
        (
            head, 
            {
                0:lambda x: x,
                1:lambda x: str(int(x))
            }[index](''.join(tail))
        )
        for index, (head, *tail) in 
        enumerate('{{:+.{:d}e}}'.format(digits).format(f).split('e'))
    ]    
    return r'\,\,'.join(
        [
           r'{} \times 10^{{ {} }}'.format(
                *[
                    ''.join(
                        [
                            parse_sign(s,filt),f
                        ]
                    ) for (s,f,filt) in (
                        (*mpair,sign_man),(*epair,sign_exp)
                    )
                ]
           ),*[
                r'{{\text{{{}}}}}^{{ {} }}'.format(
                    *(
                        (
                            [
                                unit[0],r'{}{:d}/{:d}'.format(
                                    {True:'',False:'-'}[unit[1][0] * unit[1][1] > 0],
                                    unit[1][0],unit[1][1]
                                )
                            ] if type(unit[1]) != int else [
                                unit[0],str(unit[1])
                            ]
                        ) if type(unit) != str else [unit,'']
                    )
                ) for unit in units
            ]
        ]
    )