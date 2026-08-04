import random


def gen_pass(pass_length):
    caracteres = "+-/*!&$#?=@abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    tamanho = pass_length
    senha = ""

    while len(senha) < tamanho:
        digito = random.choice(caracteres)
        senha += digito

    return senha


def gen_emodji():
    emodji = ["\U0001f600", "\U0001f642", "\U0001F606", "\U0001F923"]
    return random.choice(emodji)


def flip_coin():
    flip = random.randint(0, 2)
    if flip == 0:
        return "cara"
    else:
        return "coroa"

 
