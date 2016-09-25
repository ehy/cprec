# coding=utf-8
"""
Globals: image, license. etc..
"""

from wx.lib.embeddedimage import PyEmbeddedImage

# Two arrow images courtesy of wxPython demo/images.py,
# for list control columns indicating sort order
SmallUpArrow = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYA"
    "AAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADxJ"
    "REFUOI1jZGRiZqAEMFGke2gY8P/f3/9kGwDT"
    "jM8QnAaga8JlCG3CAJdt2MQxDCAUaOjyjKMp"
    "cRAYAABS2CPsss3BWQAAAABJRU5ErkJggg==")

SmallDnArrow = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYA"
    "AAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEhJ"
    "REFUOI1jZGRiZqAEMFGke9QABgYGBgYWdIH/"
    "//7+J6SJkYmZEacLkCUJacZqAD5DsInTLhDR"
    "bcPlKrwugGnCFy6Mo3mBAQChDgRlP4RC7wAAAABJRU5ErkJggg==")


# The program licence, encoded as:
# CHUNK = 64
# buf = base64.b64encode(zlib.compress(f_in.read(), 9))
# while buf:
#   f_out.write(buf[:CHUNK] + "\n")
#   buf = buf[CHUNK:]
licence_data = """
eNqdXFtz4zayfg7q/AiUX8au4ijx5OwlcSpVsi2PtWvLjiTPxG9LSZDFHYrUEqQ9
+venv24ABHWZ5GxqsxObZKPR6MvXF8x332n65+PoSX8cjAbj/p1+fLq8G15p+ncw
mgzUd/wC/fPJVDYrC/0h0f9oCqPPf/rpXCl9VW62VfayqvXp1Rn98u8/JfxI31TG
6Em5rN/SyuibsikWaU0EEj0s5j3FNP/yk56a9SY3+jFP5ybRkyarjf7xxx8SfVna
Gm/f97X+4cP5+fn78x9/+JvWT5O+0oNXU21L4iKzemOqdVbXZqHrUs+JHZ0WC73I
bF1ls4bI0bszWnqNh5mxSpdLXa/oyzybm8IavSjnzdoUdaLpfT1fpcVLVrzorAb5
oqx1muflm1n0FImD5fFYmXQ9yw0JQE9XxlOyellWek2ca+t3jn8XxmYvhXBYp1/o
l2/pVm/LplJLEtOiXOOJXfH7xDyzQJure1pfbonvoq5SS/zVtBYflilMleb6sZnR
0urObYTYzYraFAtZ6qVJq5R+NryU/tZSeKY8z+/f0ytr8Gkbeg2Lhu3QEniXN0pi
IR6tbizpRg+SyKzqsqY9a+lmk5PwsTjLh8/AdLVEtVryzkYSLHg3abHVJX1T6U1V
vlTpWr+tSlBu6lVZWZLSmvSA3lSNleMjlk4n5dq4z45pZGdz85LUhcQ32yov7Lts
VqXVVh/ZWVbY2qSL3pnWz2Wj52nBm91qYYZF7zi2dIJl2YPWfF6ZQr+RYDcm/QJp
sFQ9JwkegaPKLE1VYTskAXeACXRSbSpan3b4QOQPc2b3dC8+07SGVqhV+ionHGlH
ZDtiMnv86VOnO9ULq4JieyI1eKWldbYEaf2W2dVZEpaivcxN9goiTTUH6QWdTMUC
ezFka7XyH5LS0o/Rp3jHaWpHG+lzUj5NPM6FSxApdGHehF8v9wtRIk/uS1G+BbqL
EjQtKJOcLZ/OtMSntZnXYjrs4SyfSmEiWVYGkppDi6yQJ2HMsoUiZYV7gjBNwabu
FhFKYBwqbb/IoxKnUsFwK96gvNVTU/mmswqZtM3TmonPTVWntGF6Y0MPs1mWZ3Xm
/BAoi0TVwRONJZmAIyf+dbnIllBfFsUNPTBfU3jpxL9xkJxt5iudepGTrFYGZqfo
pzrjHbPP0EtDhHidhvzAS+b0j7QjI1IFCQd+pZUCyxVmpKGrPbEy/nZHnemTLRtY
ElQtUi96qiLNIzp9UonAh12RStA7a68MFFXgg5iqKAz9V1YpfzSwYXNIS0jv65Wu
3+hMa7OxP+vT8zOOSxImu1IntVSnH85IfmTnTk2iyPS2ykiokJHlh7l5ITPniGc5
GruQl8QnTDS/5zDExxivx1z3c0sSwlmYFCfG7pP8rdsKqMJYaEOi8GyNXuGdwikW
uPFRuIHi2po+s+EoxJ0WJX1fIQpteUneXSfY0EEMl3sxhpnP2A/T79cGq5jcSjDY
pNbSI6CDN6Oct7CxBhG77siImTevHKxAPqZjxZKOJCvSPKE1ZEsIMiQICu1rjqVV
uWjmwgYHEZwuaScIkGvOcfQ4hYiWcvHoHb2waWqOMKIuN3icbxNeJHZPYKleEaSg
0E1rUbiHLGsKIbx7Fxw3eFwjzpLewbeyB3ktswWvv4B3rGTHFMC8OiAyknGmIvQQ
ObGJrFhkr9miAVO6nLEjkUUCniGLL7Qh3ZyztXEcWrVk6E8KQ6am6NhzTpN0AupC
x8zKwxJfpwuAGT3PTeo4JBG4DYn5zQKGWohqOtV65+AGvDz9GnIP76UMzHoeg21w
/sFyOT6VtEPxmqAJQ6EdJK37crquRNvmggaWJdBeT/2Pw77fAMf0dDoY3090f3St
rx5G18Pp8GE00TcPY/rx8Xk4+pjo6+FkOh5ePuERv3j/cD28GV718Qsw/0OPkdMh
qOTUkYVNOxAc81ZWX5xnADKkY7MqhWgQezcA0qyvUIrW7azKHMHFplsHbdeEQEnq
rd9YqCbEH5Ghx8mH4UVPxH7yKPydEHo2JLhEMWYJ7HNYiPYA7tnvkU6e8FZmqVgz
r+ypqbWhOKdNxluOnoAG6BKr2SudGOkXUxHm2w3n6dvPYtMZ80I7p2XlXSc2p84d
ynpTVqwGDCYS5RgIOQR2AP8eq4z1LjfE5gV8B/bPJ6Zyss0mfYHITm/JM5IjWJKI
k/ABFmTwPs8bgHcsUTbQdYK07nGh/Mnok3j1EyDPAVy5swx2celiQaCAzcTqE4od
J2QofXLvrwIQSidXAKtjdtHZJINJAM8WIYt2OHW4EBfLqKypbcYmTxGUqHtVSeEt
l6pqij3RO6fskY5ZJA6xMTXyo+QGynX8iYrAelkAbi95QZwtxwB2o1nNEVHvKZry
K5+SGzQbQK+CsxLyWGBuZgifs+OifR7g+KynPgvA0UHJqgZwG7QsVvFxJ2xyURqJ
BOc9ATHp9s8krB6rOTLvbIxjcLwxuAZszgq2kDVFgYaAGBkfuXnT4l8F0WyyeVM2
NpfVyeewLyfdpd9sYOgUYGgTjBEck/FbqrU053ncJuZ5mq1JKsS0j/wX+osxG5gE
NMChOyWfWR+xgH+QHnc8oWR+2Hw6s6agVRDLaG+BtMI7DCLb/DACAl3RkSLwVrxj
c+uoNC/pdAW3tW/TUYVTkkyHwavDMeRqV1tLxpE7vRZj9umarCQAb+uopA4nlhvn
YbDnAI8i/IWg+9Vn5h40s+Z8aDXH4TumKLuqDiuM95jOsynxbPRGw3FxLewedcWJ
i6WipzHQZNfedYTOwesDoWTiNneu0hnZ7QG9JNUgwL02RpREdmFNFMd/Vlw4Ss/a
JGCeNlYyiIAZl1ku4XNOsmXB0h5h3k7lmIaFX2Wb9jkmy1t8jlDwHmiBbMspnrzV
Ez5me3ywbkIAgWwkLxKOsyyX2pJPB5k3Cs78lAFYVYewzr+zEuqwrx0X6A6WafB3
DLvLJZKgDqIiH5G6VVJIweszQhRbY1YtAhUo0DEk4EO/bH9+5qF7EL0P9AXpFeNK
QrULqc1wdoDyVJUiDJGfcZsnR0sONsoJRZTQUX5IJ1UhpHovDIuA6vHnEUEGiVnh
GEKNqVpQpK3gLTgxJO4yOPkKh0JACQot+lQUZUPeBUVAF4TZKDoeTx/0eCkTcL84
nvucAtNS/pJ4BBb0w1mB8BE+OGsLFlxdY4uPYL1ovJc2HxdT2DUYF0ZNnvv4BXKa
k91Sv2bmbccnMpUW4Z0Ovs4Nu6ufEWA7Ibu2Jl/6mqM/A+KNSSDWcUgPmiDClypB
0RF5Ik6s44H8bvYRwn+arJISjFDcIdY7I+Tu6yb87lqKClyTc9Ek6Cuv2ZoHJ6Mq
Axag5ymlgdoaV3hhASGd5E8EDB01zYTjEmoPM/CR2rIgalzKBTSqGCG2uAMvW0PW
Bz3DAtbhvTXJ+BV5WA1LiG1QThaIh000QR2La9XtPksKbYF9NqUdh8T1jtTuLI2i
c1OHD9SO0tl0HUmFvmbXwzmmuBhJTTLbCSpqN6iwY40BpwtaQsMnhe4r74VUVwJS
AG7LIZLnCQjwYJhyiK8oibujVzjayi3jQWbD0ULKIfQLTj5lW5V5SasFBQM+f/pI
vyFMS3FsSh8mUZsAnHL9vQ4O08mJgxGAUVT/Y6BqaxWXjug1ye4qdDQIBTCzUgig
9y40ndKKE4d2KU5vlPlqKkl/feFMakMoYeQHhR0lUGVFcC5HNcOnU/YgFKA9Dwuk
Fpl0ctbwdOnLC6TkybqcR/YBqRwipHaxFjtI/uU3kMgZfk71a5k3KOovKeu1dVlR
YuV8ers/wb6tF5pV3v9F3InbZJ1GlnIwyv34bai+u4Vd7pFCSjD18OfDGWJUOfs3
aiq+Bk6nN29q9jdAZAfir5p4iztnHj5oRlHHQBQ5A5TMnE1JSYMk0OKn/pxi8gZw
hfQ3nAZ+lxuOdZXUlDkQrskyCEG9RzAHkwKg2iQkcTbvrTYqKnwDCUqs6W6HD9gd
3pyoleu0ykj/G18YaouECDqCxi5IhElAZPs7S4M9MeRO9GuaZ0KOZJaTd665/ib7
2pq04kZNm1YwQGKHsE0cIHcIqkA7SwrQhTT0GBi5DpfPEBD9TOWxthNcrK8JR2GR
PVPYlXgUo3cPp3MODPwkAP+5Mzguf9nJf3EG82PalRUQgXiKKGdlfOoCMx+QxP6d
PtSRLQOjcPUszYmXQvyZgzGubSvlgSWXDwsgUXhKStv2yh2+jICgh+8DfzHW+mPj
5f0GgJoGrUNaTnKppLyjJ83MR4eZSJ+gC5BLp0G2bJ2KVMSEF24LynGsQ+TES2jG
uUptNzMjeXJH9IaThphpqcgF05fVFa8uS/p+zB5f9HtapEGulLVZC2V2eWM5M0mt
LeeZL4iRCaRQfLPMikxqrciz3Pvih6tsIx1lBGzl4xeYy1ydjGEPKuR5nsbAod0R
7fKWDv4VQge2U3Zj+MSNB7PJ3n5ic+EWH6KGq8ehm8fNwVDqCaA2/uwUabuUCx1l
ktGMMxCFczprLWGd/psRwJo0mtHpqewQHH8hNTa5QBMLN37mdqgoRlWStNqtrQm6
cZEJjre7f2RKJNWmYNzCPIellIPtqbNQLjR3pUdBfrmHFiLqgFiRBaBb4+pkrOjE
nyLqvLQbyGB0nLpWNGvDRuY9GNX6rzTgOrlmcLlDYE/7PNxmMMrE6EHDON+qQ7Cy
4yXRpAA+bl5WkW/PXMdcipzrDSVN0VBJRGSnXBQJA10Drf+3xQzQIikESbmG8j8u
ogt+jVFLB0so0VRor/m6QSGXEygX6r07j6AKupkoMJFWbGrFGOeN0WB5dPnjq8N/
oq8kOsi9orRBGKhdMEMUyXCQnb7nAbZUsEMvYEBobgoF5yo1KxaGb7Pz8SJCeIQW
1QRD/81PLmRVO34TGGPT4WNCegNf7BmgfBCNLvrfssnFs+RZSskjw72/yNH59C7O
NqGSm3onB7MZipK+Oc2q48Yt2NmG7QMUs4qjh/mCFF/Ktt1WrivpkQs/cjCoB9V2
t/chszfIeFOflVXcpFtls6yWUn2evoXuvUsU9/cjdCi4lOhNz7bSGON6RQdg7xTv
T12B8WiR/UyKO2g4zoPWyPqpK+p2zrhmAIs2NSqOfszo/9PYE44D+2pHiDspjht1
+GtP+ih1tjYOoHwL6v/BjjtDDTsG5JQfKbK3Ru/SlG8kuycyKSJG3K0lRg1+zxdZ
N/uiGu1sc6QZ6kconHvKKDK4yuWyqbhf1Rk4cTlYW1R/p0Oy6ZyrcwCs1ySKFbe4
eqprSW5CRVASZbb0/3OcU2uBrqUUuWPex05G9reeHi4lsHM5hUw0dAYQBChr/3ez
eOFanoCUKDuVnrMiJIqIY/xLS3eevn+Aeo0+lW7zOnOzha5fTebaGHuWqEgLGQyz
HFkRoDunbv4FmxKuCPkxIqF02S/ceuozH6cx6kdmUjukH5bYsZFE2m1iywgXKH5i
3RAaj38rIxdu/gmfxzX90qFxi6kdUi+brZuczNRIs0gaGBRDXhyubL2+its20bSe
obPk8nv0mQv9e4cI6O0V84jtubb//mRS6k83TM+UTS5ATmZEdVVuKU3YvueRgsi4
I5zgVyHnJ7C35DGcMjTYXItlQWFhjhENLtuHnyiNZFRB+5AtsufhxMKNfEIZiCsv
3hkJCeBZClFxnOPXZnCG6KhXCFqhHMSH/A32BcNFTZ+9ghT958rkQNKSDGOSrhCj
NIzyJPQyCRjjvMlT8rRZNW/Wlr22eLhZmrcu3MTko0lUJUVJ30/xL0VtiZ3JVTdA
WYgKqXhZdFCHnZLbpqnYgx2oudHJNC4+809i9dH0iW3HKlDoJ1XduuoZl+v8oJ6r
1UnhIKu3rhukuJotb150F1+lLqPB7iIOfZfPTdJg0y+Vo+jHMNsEu3PEAvqTUF9V
GVQfnkRC/EbGM7z2b7gkD4Fpfc/naEqMWoeRHPWCuQ4ya/E6bpmQir+hhV9xDxLT
fXssmYXy2s6uy+UkPI3o/HlZSMHbsuPkuZZ5lLOlBJb4owtXRG02od3LQ1TfL8pC
DmBB0WfBk6U8aqXtinUGYJDDe6dYEHj1/LXOyDEp4ydhXsK5QRcJxRGvyowx4XTH
amI15ZE4MIpVUN3nAac3lyTOSAzmVQxgZvajlURVW+/XHZFE/L3nm2u7dYrv3dTr
jsfKbDQ+gfaBHw7lxKiC03LZKXSl1f7Ztu1sxXm6+OgWjuzNEsErcuplO3zspwHs
0dPFQuoOUAI67heD1zcr7qB3thgNvVBck16cEkcctpLIaGZadz/tXAeQck7BIGBN
qYBqBSGuo7FuAbNASCykOTVPJbpGvphAfkkWjBaJZYcesUh2TlrpC4yu/TgrF9uD
5eSfejwJc3QUHZLy0xeVec24eytHjqHmV7mEYZU7+yMj6YIBgGJhTvQnbW+CvcU0
2HigmBThMzh34t1usorH1n2ZycJw3RdyPQIcEu7E6AJ9sDCkYjm7eBk44iXCBKW0
OUgReQSSwbUjhqNCfRX1RhwhnXFDm4Zf9G8UzXpmqnY+1OfGXM1Zcra+8+5eIiGu
Mhqoc5H2BM4bg1qVp3CStFkch2w/o9EWz6MCahdQ+yEx3yH0TJWVnxroLOUPuB3T
gzqoA+qwt/e2oSFC2B4SwU6TbBtmWEqP8/0nyE0Pc3PoToaMLv3Q8+DRz6BG1sFY
YW/+hGfhxP/GU6jW9e86FrwDqkXTuEcMEzPd+KDcDD3ge5tJO2gYokDoR8Zu7g8k
v7PcMXu94Csc5drAyKzieBCKjDZMPLtrGghiLHeuYZDlkcovWl4wMv5SpjlbN9te
9erVTmABuZxGxnnp+7YIwL/yN3w692aEUrkuQ86Omz8y27AgB+PCSPjkRfxJvm2v
Oo0e9Of+eNwfTZ/5/M97+nJw1X+aDPT0dqAfxw8fx/17PZz4qdhrfTMeDPTDjb66
7Y8/DhK8Nx7gjZgWZmQjAvTWA/88+H06GE3142B8P5xOidrls+4/PhLx/uXdQN/1
P5M0B79fDR6n+vPtYKQeQP7zkPiZTPv4YDjSn8fD6XD0kQliEHc8/Hg71bcPd9eD
MU/rfk+r84f6sT+eDgcTRXx8Gl53N3XSnxDbJ/rzcHr78DQNzGNz/dGz/udwdJ3o
wZAJDX5/HA8mtH9FtIf3xPGAHg5HV3dP1zwIfEkURg9TkhPtjPicPrBo/LueOjFD
9NX9YEzyG037l8O7IS2JyeGb4XRES/B8cV84v3q669MmnsaPD5MB6jcQIREhgY+H
k3/q/kQ5wf721A+ESLpE474/uuKD2jlIbFc/PzwhatC+767xgvIvQFADfT24GVxN
h5/oeOlNWmbydD9w8p5MWUB3d3o0uCJ+++NnPRmMPw2vIAc1Hjz2hyR+zEiPx6Dy
MBLf8qGHwyMtGXyCDjyN7rDb8eC3J9rPAU0Ajf5H0jYIMzp39XlIi+OEdg8/4U/o
QXv4z6RGD/q+/yyD2c9OPYjNMLnd1QpSilY7+5cPkMEl8TNktogRCARHdN2/738c
TBIVlICXdsPkiZ48Dq6G+A96TqpHZ30nUiEr+u0Jp0i/cER0n44TW4MeuiODDULX
Rl5HaO1duzxt197RP+jF3cMEykaLTPuaOaY/Lwd4ezwYkbzYnPpXV09jMi28gS+I
m8kTGdtwxIeisF+25uH42tsTy1nf9Id3T+M9HaOVH0iEIMm6Fg7EK9nkLGEd0MMb
Wurq1p2e7ljts76lo7gc0Gv9609DeB5ZR5EtTIZOJg+OgpMjOza+fEr74/cPDPBj
9h+v3MqYVJ+zUamwTjn+0y+f4XBHBHZclLPQYBcZFxRY83JDwdmhoXaOMrrf5qb0
XLB84fsftlaUg0iZrLEh/khq5zJupAwoJnBNeoUUQ0CPzLlzDMpq1Y0FEgPDhR0M
JnWKm9FV0NAs9uVDfyPOl2TrOnUtpxYahWHeMm6WAr9wKmTTJbYGjsPXa/8yz/dx
jwlPXI8FncFwWVRuoMjMIAGEV7N1PSsC79bBtHbYmEd4QIpp2BUXUhjY+W4/Y/iT
AAdOCM8XrmylNyVnQDyKw5N8vNFGmg58uxFxnYTkhiB/gTz5ez8xEAngHYE1dKiE
9Ixyj6WmkJ/KMFHKWsBT4b8yre5l6l8wifArrcAkEPUZ9Pwq63JeGl0g6pz3Rbjd
2DllQb/t5TCZoKwPj3seumncTmbbDm4M03rHgVJ7kUKukftF7tpmGFM57U5Jn+3j
595hAcStWJeGrTDVUzs5e9BFZkXHmci4CCU0PrjDCfkAfxFuYLhWIZd3c54Y9COd
BLRBYjdOk3D/RJieGNYTFS4YHUnk+Kj4Fi/yLOu2jsJ6rNftIEVnTuQ4YTceEbUx
W1leIJ8lXf8WBObvd+/0J//1fX6lcCmRSwTxjAjKaOKBebRArlkCLRuMqlVlQRuS
+4AE/snxZbnUPTvjGp3x1MS7R3+rJIUcqzDRm2dfxJkqnn6k99g5WblS0Rl0JQsy
bpzqY0EI+1Wgvdfvv/6U7JgzrFnrri3vfT6nXMLdIO1fTh7uCHvcPce4+YJ1wqmD
rrek4P/iu6tv73qtWez6gzb2cDAwOdaBYHfcA1NwN6lC9cgnZBfxcvN3MSM9GVxZ
bTdI87jL1c58e/6Yh/C1019/77Zzt6STRR69ffaw5MaK64W063Hj2KLGuUV5Ax03
7gdTlsb1hejq00HW3E0mqdOz/c+MWpdE8v2cOPjCZY21KRoSmFnb9+/hyTmVtk0m
fd1w49/dIXGb5dE8XEbmV2Ap5ZY+O/X33sMwsvt6baozLTe5K2WRwOfS6Shknh2t
Zlyja0tz7QWck/aeiscf2VIVuChv5b7mrZtTTzFFQUZ7ITNU/A3UVG5bPJfbcrEt
jLdxxMTZNiwk00EtA2wiQCjOBbvFidC/Ij1/h/YYTwySOVq50Gu1m1PBGIw9CyU1
Wuwf4EbfpvMvpmIX+IsMkuDqN2nJdEumVha/JvqcsFqV5fz3kAC0yIMEf1+HzfwN
r0+kQa6ue8TthiqL6xu1FQ7oT3y+XNtQ0T3Y8FcOhCZbFfuiFC3aqkSHGt6G/2KJ
UKJRfjqc72fC7Uus4uajcEJAg2e74hWjuroNUynKEfclJHEKb35I1F/qXhCg8/dn
DvxdF+rw33WxX9r8P3d/dKk=
"""

#----------------------------------------------------------------------
wxdvdbackup_16 = PyEmbeddedImage(
"""
iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlw
SFlzAAAG7AAABuwBHnU4NQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoA
AALXSURBVDiNnZJPTNNQAMbfe33703YrbFMYjAlEhhgdJhpREDUmLkr8l5gYUTQc1IMJHkSj
xhsao0avCAcNkqCJntSDCirRKImigAQkKMJgm7OTdQy6vrbb2nrSxKN85+/7Xb4fvHzjHG8r
/knAIkIieTRmvbFEyYFXjsUAwk82JzGkdBkAABcDgJQuY4h00tryrkKROYyQZixxT5CGpkPf
ENKMN0+b3UN9hwvqTzaOu4u+yPdb7/kKi4el6u1t/IP2u+WqkGMgknZkSMqJj5+ve3fk1MH3
fMjPfh3eCcWkmwz1NeQBALXxz7vMAIDkr+gKGmNFvH3teQU2EbKjpuUTno5ttCOkZXsfXfTE
Y8tzWfus6PO/nHnY1rHelTcVh9AAs7wPJ4VlqipzuP/1sZJy/4uZ3Q1nR6I9G8woIZbSFqso
KbJdU2UOma1EGu3fz0RDlUvWbekcpLCSmo97LV8G9tgQ0rIAGNmaQOsnAEASIEOkvNUXzrg8
kz/rTzZ2x3kfFQ1VeiNT6/N03YwnRgKlC3OenEyaNSGki4jKqlwuLwz2HV25trZrgITyDVjb
LMQsNlEyWyQyP1dYQNsSiazKME2XNrVirOh82M913Hx82rk0OGV38MKBE8e726/0Hst1hvlA
5fXXcN+lj70Mk9aqpk3UVjTxI/y9anWppKpeSdNMSTtnIEMfozmHxMmS3R2czikdDU3mZ7Qu
y6qidWWdH2FkzUhP4VhFLcxg+s+/uikjpyomP8S39Q1QhDYzwWUFrrdVdShtZv92LOlUsObD
M4zTJgXo8B+RDKxJav7sV4owKZilEMxgFhhQ/8ciHQKTYlXgrd69gTKvkC6/2uSnfxQsNQu5
Trxgc1ES66JkqxNAQ9cYWciyJJHlRCHtmhNISeTXeMvN0fC3IiuGwEhIZUEydOfMq/92ecLD
YIAMAQCg/vcYAACRLuPMPBuP969azB4osw7xN+nST7zu6AufAAAAAElFTkSuQmCC
"""
)
getwxdvdbackup_16Data = wxdvdbackup_16.GetData
getwxdvdbackup_16Image = wxdvdbackup_16.GetImage
getwxdvdbackup_16Bitmap = wxdvdbackup_16.GetBitmap
getwxdvdbackup_16Icon = wxdvdbackup_16.GetIcon

#----------------------------------------------------------------------
wxdvdbackup_24 = PyEmbeddedImage(
"""
iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlw
SFlzAAAKYQAACmEB/MxKJQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoA
AASKSURBVEiJvZVrbBRVFMfPnbkzu/PYbrvPPpc+QFKaRmhKiwTBqICCiQgoxqBC6of64PFB
YqIkBuMHE6MJ+IDEhGBSSVALi0GhbQKCBYOglEBopbTsbrfdbndnO7uzM7s7Tz+YJhjaCGo9
327O/5zfubn3nIP2vP/OOEFrNMyCmSqlYYQNunFXBzEbgOsfv2BhgjQKAGACAPqvAQRp6BiR
Zh4A9Bk0/wqKSNOcAqj3G3tvAANhhI0cABTuJ/CeqyBNEiPCzFsAub/T/kMAxog0lZGhFtzf
t8Y/5WBYUfOUDmYDcy9mOEdSAwDIy8X43KkdcxAgVD6nL93QHEwCANy8tsoVurm0pKr2sli/
6IRgmhj93NNeKWc9tJWy5TGBDfnimbb6/itPzeMcCdnlDaVFIVAkpf18iTc02b770dMYF8zO
g/tbhweWBwAA/BX9iYbmYAQA4EL3a4tGhheXs3zq0lh4IRn8cl+LEK91LWg6Mdjg7RohEGko
0dvNPgCApmVfXX1p58aehubjNwAA1LyDIgg923tyZ9nwwPJAWeBqlCR1IxmvKzEMOmdZSImP
NrgBAGKRRv7QR8GVObmEfmbLtq4Nbe0XaFrJYEn1m5JY6gQA6O3atqT31PYllkUQdjad3dT+
8vFoqIk6d3JHq82ezW14pb2nY++RtaIQ8A3deITFuGCoBdYGADDQt6beVz4Q3bz9+S7OkVAB
AAhsYBwSWtwAAHYmI63bsu1YIc/jsyfeXJFK1FScDr79YEqo9hkGTVXVXf792qX1PpLUVQCA
4f4VbgDLAgAo9kRiiuQpTsbrSvuvrC1uXn4o9OcjGyQeT9eXAwA43dExhpsUxWTArcguDgBA
FKqKM6lyH8OKohCv8wrxWq+u22gAgNHQQp9lkgQAwNwFp/vmNpyJdB7c/2LXN++ty+ccR5et
/mQAYQNQ6/ZcWtPtRVM/CFP5HMtNCsXukVhkqGUxw4qpV99dsY+3ixp/q5oNT9Q7Pzty4A0b
I6VNA2NNZbhN7Vv3PtDYHR+8ttLfefDzNl2zsw89fuDb+dSPv6FPf9j4esWTFyg2XGmv7Fhf
w4yWFtFJF0+JTo4SizhK4nlS4jisMCxYBAEAYJGGYXCKrPOyrBVls7ozI6suMat6UrJcG56M
bP06pDkz+lh3q4a6d3/4VtPZh1exw4FqZBJ3T1XCMuXqkUiuaixR8CcyVMZhpyc8TnvM57HH
fKXTNZhJ6Wq2/tbQT892fo9SNaEeGyDfTN2YeKz3lytf7Do/nW/p6sNP84M1tTPFpl2T19G5
PR9snn9+yVpmtLQMLDTdXrCU6uhIwZsUC14hSxiYoBMu3h7zu+0xX9l0iS3S1JWaSOTXTUeD
qCPc1MwFxiu4W9VMWfCJCtuEh6MnnSyWeAZLPEvKDEMqDIsMEv8lCaWpBpvP6Zys6A45pxdJ
ilqSyeUrxzLR574bVb0pTRn1xtAxq3weANTMdM0psyXcmL0dYExKM5XacF5zSsYM0jsHYxjP
ILrLCl5BL3gF6R6k1p2HWdnF/ysAA0AGAMZmKX/6D1Z7+8SbucfAAAAAAElFTkSuQmCC
"""
)
getwxdvdbackup_24Data = wxdvdbackup_24.GetData
getwxdvdbackup_24Image = wxdvdbackup_24.GetImage
getwxdvdbackup_24Bitmap = wxdvdbackup_24.GetBitmap
getwxdvdbackup_24Icon = wxdvdbackup_24.GetIcon

#----------------------------------------------------------------------
wxdvdbackup_32 = PyEmbeddedImage(
"""
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
"""
)
getwxdvdbackup_32Data = wxdvdbackup_32.GetData
getwxdvdbackup_32Image = wxdvdbackup_32.GetImage
getwxdvdbackup_32Bitmap = wxdvdbackup_32.GetBitmap
getwxdvdbackup_32Icon = wxdvdbackup_32.GetIcon

#----------------------------------------------------------------------
wxdvdbackup_48 = PyEmbeddedImage(
"""
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
"""
)
getwxdvdbackup_48Data = wxdvdbackup_48.GetData
getwxdvdbackup_48Image = wxdvdbackup_48.GetImage
getwxdvdbackup_48Bitmap = wxdvdbackup_48.GetBitmap
getwxdvdbackup_48Icon = wxdvdbackup_48.GetIcon

#----------------------------------------------------------------------
wxdvdbackup_64 = PyEmbeddedImage(
"""
iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAABHNCSVQICAgIfAhkiAAAAAlw
SFlzAAAbrwAAG68BXhqRHAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoA
AA5LSURBVHic7VtpcFTXlT73vve6X2+vpW7tCxISSGgDhCWBjWwcDAQK7NgMxI6xnfEUdsaZ
qZoQqErFcaKpmZqq8SzJjFPjjAk2wbHjxMEERGFXPGBWAbaIZbBA+9qSWlJL3eq933bv/JBa
9CZAsWyVI39Vr0rvrueed853zr23herq6g4BwC5YmLjAAsBDiCEAQPF8S/PFAlGq4tUsACgI
EyoU9RNzUb8632J9EfDb0rHz6lJMVaywACAjTKku3alaVnSI8y1cDNDnNC7n+rSQAwCZBQAF
ECEIUQIAC8ICAFGMMGVhSgEywpQAoioAKPMs2hcCBMAAJhRuWgClgIDAAlEAIGARpgQiLQDB
nFnA5+W3cwhKUIQFyAgTEmEBX4IFfEYgUCHSAgBRFRYSCQJVESbRLgAIFg4JIlARolEkOJcc
8Hlh7lwTAYmxALLQXEABTFWIcAF1IbkAAKhTiZ8SJkGCFlAiFBcF0KQ5LBwFAFWnPnhUGFQg
sQL+4vIChCAqDCoIURUQELpASJDGkuDky8LiABShAAUhooRdYGx4qc7tzNHesj8iwOvdis7g
lA2mcUWj9c/KcsaGl+jc47kJ51i09LKH0wTJTH172mrNROUQRLimURiV0nOuB2bq09exRlBk
3fSJV8hu0Xm8uZxPyjBNWwCaDINq/a9/Vj7YW5k6mwXpDBOhrLxPxgtLT4+s/tqBwVu19biy
NL/66bG7g/4kPlH99r957nLZXfWORHU+Tyr3xku/XRtLS1X3HWrb8ujz7YnmOnropeV9HXdn
xtYlG2yhEu6kOBkFEFUAUVWReTI8UGa51QISIehP4rtu3J/ddeP+7JamrZmPPfftRl7nibMK
ShEcPrC/ZqbFAwD0ddxjLrur3p6orrN5Q0oiTs4vahiFGPe9cu7bWR/U/3ClGDRFWRrGKlmx
4vf9y3Sngr6O7LEIDgClo3mDWVU0TOwEGt4nmcwjvvB7KJDE+71WfSIhbV01mR9feCLjno0v
98XWnfrDj4sGeyvTEy99EkN9Kyyxiwmjp32tNbYMMwopLD3jgCkC97rTNccOvVTZ01a7KLZt
Ukr/xIO79jZakA2PXylJhek8YNIClM7m9WmJJi6vOtq29Vs/aI4sGx8t0B38j/pNQX9ynCJs
3dUWAOiKLOu8vt7y4endFTOufAoOe5GFEEbFWKWxdUN9K1Niy1LSO8c0Wr8IANDU8Hj2yaMv
VIcCZl1kG4QJXbH69ze2PPbDZpYViacj1xIbBRSEqGrrrkqogMLSM4Nw86sgAABrWrfPktbj
HOyJV0CS1eaBiJAa8Fm5+l//dC0hTNTRe0HJue7ulvsKIssUmef6O9eY8osaXJHlQX8S6xrL
S46dKyvv6ojfm4KPHfrvqq6W+wtj64XkIffWb/3g4pKyD8anFYKoijBRAEDGMJUHhEICco4u
jjMxlhPlpWWnRqcWFA6VyrUPd6QN9qzKiW2v1XmDa9bvbw+3AwDlnQOvVPu9qcYYwSa+uXt3
g8E47osdo7v1PmtkfwBQ2q5ttlKC4whAUTTwi38+uy128QhRWlZ1rPm7P1lXv6Tsg5Go8dBU
7hMZBnv61looxXGXIywrykcOvrwq/O73phgcQ8XpoaAQ9+V1BpfvwSf2fmC2DEwv6syJfUW9
HXdHfWXMqGTbrn2nOd4vWtK6HX6fNUo5gz2rUiCGB3rb1iaMTM2Nj8S5lVFwuDd/80fnSipP
jCTqM7UblCHCBWTbQHVC9g8FBX3rJ1vKEw80CV7v9q9Y83bTPRtfbjcKo1K4vK9zTfLF9//+
ntj2lWvf/Kiw5OwIAEBaVtuorbt6cWS9Y6g4HWIUMNS/IuNWMkwtDIqXv9/80JN7PuT17pmT
uslUWIUpF5ARoop9pCyOYO4UoYDZcONPD5X1tNUmw5SrSCEjHP3VzzeoCsdGtk3J6BjcvPOF
j8PtMhddjftKfp/VNDa8RBtuI4aM4HLk3zY30WgDoZr7X/2U17tDEONCUc8k6d+0AK+Yyni9
GULcgLwvULbqeFP4XVU5xjW2KNk1lp/qc6dFWYzXnZ5c//rPHjIJI7/JL25wvvPaL+71uLKi
OIXjQuL2p7/7R4xVOVxWUHI+Ycxvb96UlpLR2QkA0Hp1SwYhTFx4RlglNIJYJdHA/+6Vgw8/
8vTfHS2q+L/RmRSFJnlPmVaAzVEVR34AABk5zb3bdu27HFtOCIN+/pPLT3hcWWnR5Sxz5fxT
RXbb8pHO6+uXx/bLKWhss3XXmG3dNebIck4TDMmSLio5GuiqzoAN0AoA0NN6X1wmhxCl33jy
e2+/+9sXvyGJ+umwJ4kG3Tuv/u/2B5/Ye6S86uhQYg1QBUVygN1VltC8FhU29kCCpARjFbLz
m7piFQAAIEs69uyJfZsSjdfTdu/ynrZ74xSTCCODJZnhue39Fdmx9aYk+2hFzZE+vdH51uED
v3xMEvXTpKzIvLb+9f/aIYWM76yqfSMuIQME0ySIAUAecxckJJjSVce7IIEPBXwWNNBdFRdz
AQCGbeW5ssTPmOreKdyu7AwxaEKyxFOXIz8rtj4tq7UfANTC0jPDO3Y/86ZG6/dH1qsqx733
u3/ZcfnUdxbDzRA+9VAFIaICgMLaxZIUUTYZYyfQG8fHzVabLxQUEACALOmZseElxu6Wddmf
Nm5f43Wnx319jgsFfZ74cl7vdt9qsZQiJAaFKA6iBOOWpq1pDCsTVeW42D45i//UC1MWUlh6
xr5j97OvHz6w/ylJNBjCbQhh2ZN/eGGHGDIeWbf1P2+Ey1GEBbCD4vKSREIFfFbrv+9ref5W
gkfCYBx3BHyWuEiSt/RS41Pf23H8Vn1VwqIX93Q8ryqaqI1Lb3ttNqC4jBgAAEoqT3RDhHtO
KeG1wwf2Py2JhukPSinG59/bs10SDczG7f80SegRHIDdSsYtY/ztoOV9nvziC5dkmecpoKhM
TW90ju3Y/ewJiDPB6IfBiiIkD8Vto0cGS3Pt/RVxmxq90TmWktHhiR2nsPTM8M5nnvmlRuv3
RranFOHLp77z8Inf/Fs1AKiTCiCTCgipwm03KAAADCNLvN7tFJKHbKmZ7S35RRcvbnn0R/v3
vljxrz53hkUSDabI9ggR9es7f/yW3ugM3U4BAKCmpHfbYud0OvIWTYzl5cWWW9O6emYap6Dk
7MjOZ3a/otH6PDHd0McNux48cvB/ahECJbwXQHV1dRvTa69+zVgwiEwFg+MwS3BugbVcrLKY
r5ZadH05Ztav1zJBnmMCvAaHtBwT4jVY1GiwqOWwyGmwpJl6OA7LHEexSohGlohGlolGkohG
lohWlIlWklRelIguJKm8KKu6kKTqg7JsmQh4SzqcrupPxj0VrXH7iDtBYCjV7OnIFYZP3/Xu
ZCrMEBlhgmGGQ1EscSj5o8okc1O5xdhWaNX3ZVt4e7pV67BaWI9RgBjTv1NQTAgAgrBSAG4S
2J2AcLIkWV1OMd0xHsyxOwMFfU5Pedu4a3WTM5A3EJqpH5p0AQkirsZkQJSBCAUY2woN+Qce
L7KeW1Oi783NRSqOy8QAAChD5u0gFRGMtA6rVeuwWoXmZVF1isnnmahsbh9++I8ttsePDFA2
4nwBUQVNyj2tAAlhygrXSvi8g48WWxpqSvT92blAw+dPlFJG/VKdGDMBnd7aUL3S2lC9ctk/
ft/nXnGjfXjbyVbbk4f7I0hQQXV1datqkqW/qnprx3rBlp0OiaPOZwLhpZCYNjYWzLY7/Et6
HZ6KFods9koAAPxQhkHfn2XSDqcJ2lGroHElmbgJs8B6jAJSGHbGQf/M6xqVDwWH1l26fn73
683979e8i1qLW5/L8pr/ATOEw3N4L0C0Umh047nG3mffuO5eed17+x7RQARD/itPFmS/va3S
0JVfcPses5ANgPGmjjneXXFlLwrywZOyZSILaWSMAc2JAihWSdNrew+NrbvknIvxVj/y6tfN
n5R/pnwlEgQoQ1SMPZQeZAFAoqwqAatiSudIAYyqIpmds98bqPpgkDKqdPuWdwYKlKGIYibE
EdSf2//XAkP/FmlkFgOas7tB1RDwjW4439S1Z//1UObonyV8Zv2mtNxDO1cKzcXL5vKOlgBl
gibfxNmCtj2orq4u6wEDfnTZka2beLc5blMUjdkzJGUVJZThGA3mDo36irscwUWDPsnqEkPp
DlFMd4i6wUze2LpE0PfmmPjhdJN21CpwriQTNyEIrDc6u5wLUIaozpXNnZe+//LltmP3vscC
gNy7/USP/dk338i9VG3KOL6xQLhWUshNCElzMyMC3p6WwtvTUpI/Wnnn/RAAZefG7CmjKoHF
/bbxtVe6B3Yd6fMZvaCOJwGET4WxRpYQJtqRzadHRjafHgGAS6mnai0ZxzcuNl8rXcw5k2Z9
XTbfoKwi+wv6+p21jT22XUf6JavrJr8FeBZzys1fiDAaWUKsKkMEaTkeuOBwPHDBAQAfGTrz
dUlNFWZDZ76gG8g0a0dTzNx4kpnzmgQgaF7/z4DwYlBO8njElHG3mDnqDuQPuD2l7e6Ju655
VEMg4S0zYggwGvnmzRDDSyJmiAwACTv4l/T6/Et6fQAQtWXFMofMH5cbhevFZn1vjqBxWI2M
qOWwpGGxyLFI5lgscxySWRbLHIsUhsUyy0GC+wcAoJRRVMqpMmFlhXKKQjhFJhpp8m+tJBON
pChGvxjMsXt8Rd1ud2WzJ5hjn7WbIEalWCvd3Asw+pCMJlPdWbEc4WRwrW6acK1umphNPyag
wxpnEsu5BVbVSkS2TChykluheMafBcwpEKaE0coSACiIUgpHIbsaAOLu3f7CEXwYBs8vsP8T
isdXCphvAeYbXylgvgWYb3ylgPkWYL7xlQLmW4D5xoJXAKL0czgG/hLh/wE3bPMpxXbbhwAA
AABJRU5ErkJggg==
"""
)
getwxdvdbackup_64Data = wxdvdbackup_64.GetData
getwxdvdbackup_64Image = wxdvdbackup_64.GetImage
getwxdvdbackup_64Bitmap = wxdvdbackup_64.GetBitmap
getwxdvdbackup_64Icon = wxdvdbackup_64.GetIcon

