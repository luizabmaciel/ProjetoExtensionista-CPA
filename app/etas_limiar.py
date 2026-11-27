"""Em que nível do Guaíba cada ETA parou em maio de 2024, e o que isso diz para um nível escolhido.

Ideia
-----
As notas do Dmae dizem o DIA e o PERÍODO em que cada ETA parou (ex.: "manhã de 04/05"), mas não a hora.
1. Transformamos o período numa JANELA de horário (ex.: manhã = 6h às 12h).
2. Se a nota foi publicada no mesmo dia, a parada aconteceu ANTES da publicação: a janela termina ali.
3. Com a série do nível do Guaíba hora a hora, lemos o nível no início e no fim da janela:
   isso dá uma FAIXA de nível em que a ETA parou. O meio da janela dá a estimativa central.
4. Sem a série, só usamos a única leitura com horário que as fontes trazem (5,09 m às 12h de 04/05).

Suposição: o nível subiu continuamente durante as paradas (o pico de 5,35 m na régua do Gasômetro veio depois).
"""
import numpy as np
import pandas as pd

# período escrito na fonte -> (hora de início, hora de fim)
TURNOS = {"madrugada": (0, 6), "manhã": (6, 12), "tarde": (12, 18), "fim da tarde": (15, 18),
          "final da tarde": (15, 18), "noite": (18, 24), None: (0, 24)}

# única leitura de nível com horário nas fontes (nota da Prefeitura F13, régua Sema/ANA)
LEITURA_CONHECIDA = (pd.Timestamp("2024-05-04 12:00"), 5.09)
RECORDE_2024 = 5.35 # régua emergencial do Gasômetro (87444000), mesma da série horária

# qual evento de cada ETA marca a parada ligada ao nível do rio, e a ressalva de cada uma
EVENTO_LIMIAR = {
    "moinhos_de_vento": ("suspensao_saa", "o Dmae também registra a parada da ETA na manhã de 04/05 (fontes divergem)"),
    "tristeza": ("suspensao_eta", None),
    "sao_joao": ("suspensao_eta", "desligamento preventivo por risco de choque elétrico; fontes divergem sobre a causa"),
    "ilhas": ("suspensao_eta", "captação no rio Jacuí: o nível medido no Centro é só uma aproximação"),
}
FORA_DO_LIMIAR = {
    "menino_deus": "parou em 06/05 por alagamento interno, depois do desligamento de uma casa de bombas pluvial; "
                   "não dá para ligar essa parada a um nível do rio",
    "belem_novo": "não parou em 2024",
}


def janela_da_parada(evento):
    """(início, fim) da janela em que a parada aconteceu."""
    h_ini, h_fim = TURNOS[evento["periodo"]]
    dia = pd.Timestamp(evento["data"])
    ini, fim = dia + pd.Timedelta(hours=h_ini), dia + pd.Timedelta(hours=h_fim)
    if evento.get("limite_superior_pela_publicacao"):
        fim = min(fim, pd.Timestamp(evento["limite_superior_pela_publicacao"]))
    return ini, fim


def nivel_em(serie, momento):
    """Nível do Guaíba num instante, interpolando entre as leituras vizinhas da série."""
    # datas viram "segundos desde 1970" dos dois lados, para a interpolação comparar na mesma escala
    origem = pd.Timestamp("1970-01-01")
    x = (serie.data_hora - origem).dt.total_seconds().to_numpy()
    t = (pd.Timestamp(momento) - origem).total_seconds()
    return float(np.interp(t, x, serie.nivel_m.to_numpy()))


LACUNA_MAX = pd.Timedelta(hours=3)   # mais que isso sem leitura: a interpolação é pouco confiável


def lacuna(serie, momento):
    """Se o momento cai entre leituras muito distantes (ou de estações diferentes), devolve
    (leitura antes, leitura depois). Se não, devolve None."""
    antes = serie[serie.data_hora <= momento].tail(1)
    depois = serie[serie.data_hora >= momento].head(1)
    if antes.empty or depois.empty:          # fora do período da série
        return (antes.data_hora.max(), depois.data_hora.min())
    a, d = antes.iloc[0], depois.iloc[0]
    troca_estacao = "estacao" in serie and a.estacao != d.estacao
    if d.data_hora - a.data_hora > LACUNA_MAX or troca_estacao:
        return (a.data_hora, d.data_hora)
    return None


def limiares(etas, serie=None):
    """Uma linha por ETA: janela da parada e a faixa de nível em que ela parou."""
    linhas = []
    for e in etas:
        linha = {"eta_id": e["id"], "eta": e["nome"].replace("ETA ", ""), "inicio": pd.NaT, "fim": pd.NaT,
                 "nivel_min": np.nan, "nivel_max": np.nan, "nivel_central": np.nan, "ressalva": None,
                 "confianca": "-"}
        if e["id"] in FORA_DO_LIMIAR:
            linha["ressalva"] = FORA_DO_LIMIAR[e["id"]]
            linhas.append(linha)
            continue
        tipo, ressalva = EVENTO_LIMIAR[e["id"]]
        evento = next(ev for ev in e["enchente_2024"]["eventos"] if ev["tipo"] == tipo)
        ini, fim = janela_da_parada(evento)
        linha.update(inicio=ini, fim=fim, ressalva=ressalva)
        if serie is not None:
            a, b = nivel_em(serie, ini), nivel_em(serie, fim)
            linha.update(nivel_min=min(a, b), nivel_max=max(a, b), nivel_central=nivel_em(serie, ini + (fim - ini) / 2))
            buraco = lacuna(serie, ini) or lacuna(serie, fim)
            if buraco:
                aviso = (f"baixa confiança: não há leituras do nível entre {buraco[0]:%d/%m %H:%M} e "
                         f"{buraco[1]:%d/%m %H:%M}, e a faixa foi interpolada")
                linha.update(confianca="baixa", ressalva=f"{ressalva}; {aviso}" if ressalva else aviso)
            else:
                linha["confianca"] = "boa"
        elif fim <= LEITURA_CONHECIDA[0]:
            # sem série: sabemos só que parou antes das 12h de 04/05, quando o rio marcava 5,09 m
            linha["nivel_max"] = LEITURA_CONHECIDA[1]
        linhas.append(linha)
    return pd.DataFrame(linhas)


def situacao_eta(limiar, nivel):
    """Situação de uma ETA no nível escolhido, com base no que aconteceu em 2024."""
    if limiar.eta_id == "belem_novo":
        return "operou" if nivel <= RECORDE_2024 else "sem observação"
    if limiar.eta_id in FORA_DO_LIMIAR:
        return "outra causa"
    if pd.notna(limiar.nivel_max) and nivel >= limiar.nivel_max - 1e-9:
        return "parada"
    if pd.notna(limiar.nivel_min):
        return "incerta" if nivel >= limiar.nivel_min else "operou"
    return "sem dado"


def situacao_bairros(situacoes, eta_bairro):
    """Situação do abastecimento de cada bairro, a partir das ETAs que o atendem."""
    m = eta_bairro.dropna(subset=["chave"]).merge(situacoes, on="eta_id")

    def resumo(s):
        if (s == "parada").all():
            return "sem abastecimento"
        if (s == "parada").any():
            return "abastecimento parcial"
        if s.isin(["incerta", "sem dado", "outra causa", "sem observação"]).any():
            return "incerto"
        return "abastecido"

    return m.groupby("chave").situacao.agg(resumo).rename("abastecimento").reset_index()
