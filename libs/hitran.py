CH4   = 0
CO2   = 1
C13O2 = 2
CH4v3 = 3
CH4v1 = 4

# A3 means I don't know
P,Q,R = -1,0,+1

ch4v3_r_branch = {
    1:{
        3:{
            29:3006.2595 # corrected 2022-02-04 csr
        }
    },
    2:{
        4:{
            40:3013.967
        }        
    },
    4:{
        7:{
            58:3037.5875 # PF updated 03012022 to joern exp data 29.05.2017
            #58:3037.604293 onenote value
        },
        5:{
            # 53: 3035.526783
            53: 3035.52858 # updated 20220304 (CSR) 
        }        
    },
    5:{
        7:{
            72:3089.939,
            #70:3047.668710  # added 021622 PF stronger einstein than 72
        },
    },
    7:{
        8:{
            83:3068.165 # modified 20220316 csr
            # 83:3068.168
        },
        9:{
            84:3067.824960    # added 021622 PF stronger einstein + higher frequency + r instead of Q(7)9 branch
        },
        10:{
            91:3068.482
        }
    },
    8:{
        9:{
            94:3074.681
        },
        11:{
            99:3078.346
        }
    }    
}

ch4v3_q_branch = {
    3:{
        4:{
            40:2984.232
        },
        6:{
            32:2983.386
        }
    },
    5:{
        6:{
            59:2983.396
        },
        8:{
            #54:3019.346048
            # 54:3019.3565 # 03022022 pf
            54:3019.35938 # updated 20220304 (CSR) 
        }
    },
    6:{
        8:{
            71:2985.094,
            #70: 2982.330027 # added 021622 PF stronger einstein than 71
        },
        9:{
            66:3021.788
        },
        10:{
            65:2981.202
        }
    },
    7:{
        9:{
            80:2981.831
        },
        11:{
            73:2981.891
        }
    },
    8:{
        12:{
            85:3015.850
        }
    }
}

ch4v3_p_branch = {
    8:{
        10:{
            74:2934.904959 # n" was missing beforehand, changed 03022022 from .913 to .904 pf
        }
    }
}


ch4v1_r_branch = {
    0:{
        2:{
            15:2956.851
        }
    },
    3:{
        5:{
            44:2991.699
        }
    },
    4:{
        6:{
            49:2991.274
        }
    },
    8:{
        8:{
            # 10:3029.419498 # was missing beforehand PF 021622
            10:3029.4233 # updated 20220304 (CSR)
        }
    }
}

ch4v1_q_branch = {
    6:{
        7:{
            # 57:2942.158
            57:2942.1539 # updated 20220304 (CSR)
        },
        8:{
            52:2943.515
        }
    },
    7:{
        9:{
            61:2942.956
        }
    },
    8:{
        10:{
            69:2940.079
        }
    }
}

ch4_r_branch = {
    0:{
        1:3028.75226
    },
    10:{
        2:3122.76422, # 2:3122.76252,
        1:3122.331605
    },
    9:{
        1:3113.380273,
        2:3113.261511
    },
    8:{
        1:3104.585504
    },
    7:{
        2:3095.179237
    },
    6:{
        2:3086.03076,
        1:3085.832219
    },
    4:{
        1:3067.300026
    },
    3:{
        2:3057.687423,
        4:3057.761166,
        5:3057.726929
    },
    1:{
        3:3038.4985
    }
}

ch4_p_branch = {
    1:{
        3:3009.0114 
    }
}

ch4_q_branch = {
    1:{
        3:3018.8243
    }    
}

ch4_branches = {
    P:ch4_p_branch,
    Q:ch4_q_branch,
    R:ch4_r_branch    
}

co2_r_branch = {
    0:3715.555972,
    2:3717.085279,
    4:3718.589313,
    6:3720.068066,
    8:3721.521534,
    10:3722.949725,
    12:3724.35265,
    14:3725.730332,
    16:3727.082797,
    18:3728.410081,
    20:3729.712228,
    22:3730.989289,
    24:3732.241323,
    26:3733.468396,
    28:3734.670583,
    30:3735.847968
}
co2_p_branch = {
    12:3705.001285,
    10:3706.694136,
    8:3708.361953,
    6:3710.004678,
    4:3711.622263,
    2:3713.214664,
}

c13o2_r_branch = {
    0:3633.683611,
    2:3635.209416,
    4:3636.707085,
    6:3638.176605,
    8:3639.617966,
    10:3641.031164,
    12:3642.416202,
    14:3643.773085,
    16:3645.101826,
    18:3646.402442,
    20:3647.674956,
    22:3648.919397,
    24:3650.135799,
    26:3651.324201,
    28:3652.48465,
    30:3653.617196,
    32:3654.721899
}

c13o2_p_branch = {
    32:3604.480652,
    30:3606.464049,
    28:3608.420299,
    26:3610.349299,
    24:3612.250952,
    22:3614.125167,
    20:3615.971858,
    18:3617.790947,
    16:3619.582359,
    14:3621.346025,
    12:3623.081882,
    10:3624.789872,
    8:3626.469943,
    6:3628.122048,
    4:3629.746143,
    2:3631.342192

}

co2_branches = {
    R:co2_r_branch,
    P:co2_p_branch
}

c13o2_branches = {
    R:c13o2_r_branch,
    P:c13o2_p_branch
}

ch4v3_branches = {
    R:ch4v3_r_branch,
    Q:ch4v3_q_branch,
    P:ch4v3_p_branch 
}

ch4v1_branches = {
    R:ch4v1_r_branch,
    Q:ch4v1_q_branch
}

mols = {
    CH4:ch4_branches,
    CO2:co2_branches,
    C13O2:c13o2_branches,
    CH4v3:ch4v3_branches,
    CH4v1:ch4v1_branches
}

def get_line(mol,line):
    keys = [mol] + list(line)
    d = mols
    while keys:
        key = keys.pop(0)
        d = d[key]
    w = d
    return w