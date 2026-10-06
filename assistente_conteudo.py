"""Textos do assistente offline: conversa, ajuda do sistema, glossário e variedades.

Tudo aqui é conteúdo fixo, sem consulta ao banco. Os trechos entre {chaves}
são preenchidos pelo motor (assistente.py). Em "chaves" ficam palavras já sem
acento e em minúsculas, porque o motor normaliza a pergunta antes de comparar.
"""

# Conversa -----------------------------------------------------------------

# (expressão regular, respostas possíveis). O motor escolhe uma ao acaso.
SOCIAL = [
    ("agradecimento", r"\b(obrigad[oa]|brigad[oa]|valeu|agradeco|agradecido|agradecida|thanks|vlw)\b", [
        "De nada! Se precisar de mais alguma coisa, é só falar.",
        "Por nada. Fico feliz em ajudar!",
        "Disponha! Qualquer dúvida, estou por aqui.",
        "Imagina, é um prazer ajudar.",
    ]),
    ("despedida", r"\b(tchau|ate mais|ate logo|ate amanha|ate a proxima|flw|falou|fui|adeus|ate breve)\b", [
        "Até mais! Qualquer dúvida, é só chamar.",
        "Tchau! Foi bom conversar. Volte sempre.",
        "Até logo! Bom trabalho por aí.",
    ]),
    ("como_vai", r"(tudo bem\s*(com voce|contigo)?\s*\?|como (voce )?(vai|esta|ta)\b|como voce se sente|td bem\s*\?|tudo certo\s*\?|tudo joia|como vai a vida|^\s*e (voce|vc)\s*\?)", [
        "Tudo ótimo por aqui, obrigado por perguntar! E com você? Em que posso ajudar?",
        "Estou muito bem! Pronto para ajudar com o sistema ou com os equipamentos. E você, como está?",
        "Tudo certo! Sou um programa, então não me canso. Como posso ajudar?",
    ]),
    ("estou_bem", r"^\s*(estou|to|tou|tamo|ando)\s+(bem|otimo|otima|bom|boa|tranquilo|tranquila|feliz|ok|de boa|ótimo)\b", [
        "Que bom saber! Posso ajudar com alguma coisa?",
        "Fico feliz! Se precisar de algo do sistema, é só pedir.",
    ]),
    ("estou_mal", r"\b(estou|to|tou|ando)\s+(muito\s+)?(cansad[oa]|triste|estressad[oa]|mal|desanimad[oa]|sem paciencia|ansios[oa]|sobrecarregad[oa])\b", [
        "Poxa, sinto muito. Se eu puder tirar alguma tarefa do seu caminho aqui no sistema, é só dizer. Quer uma frase de ânimo?",
        "Entendo, dias assim acontecem. Respire um pouco. Se quiser, eu cuido da parte chata de consultar os equipamentos.",
    ]),
    ("quem_e_voce", r"(quem (e|eh) (voce|vc)|quem (e|eh) tu|qual (e )?(o )?seu nome|como (voce|vc) se chama|seu nome|voce (e|eh) (um |uma )?(robo|bot|humano|humana|pessoa|gente|ia|inteligencia|maquina|programa|real)|voce (e|eh) de verdade)", [
        "Sou o assistente automático do sistema Ativos Escolares da {escola}. Não sou uma pessoa: funciono por regras, sem internet, e conheço bem os equipamentos cadastrados.",
        "Sou o assistente do Ativos Escolares. Um programa, não uma pessoa, mas bem atento ao inventário da {escola}.",
    ]),
    ("quem_criou", r"(quem (te |o )?(criou|fez|desenvolveu|programou|inventou|construiu)|quem e seu (criador|dono|programador)|quem (esta|ta) por tras)", [
        "Faço parte do sistema Ativos Escolares, feito para a {escola}. Quem cuida do sistema é a equipe responsável pelos administradores.",
        "Fui feito como parte do Ativos Escolares, para ajudar a {escola} a cuidar dos equipamentos.",
    ]),
    ("idade", r"(quantos anos (voce|vc) tem|qual (e )?(a )?sua idade|quando (voce )?nasceu|que dia (voce )?nasceu)", [
        "Não tenho idade, sou um programa. Mas estou sempre atualizado com o que está no banco de dados.",
        "Idade não se aplica a mim, mas sei exatamente quantos equipamentos a escola tem hoje. Quer ver?",
    ]),
    ("gostos", r"\b(voce|vc) (gosta|prefere|ama|adora|odeia|sonha|dorme|come|bebe|sente|tem (fome|sono|medo|familia|amigos))\b", [
        "Gosto de inventário organizado e de ver tudo no lugar. Já dormir e comer eu deixo para vocês.",
        "Sendo um programa, minhas preferências são simples: dados certos e perguntas claras. E as suas?",
    ]),
    ("elogio", r"\b(parabens|mandou bem|muito bom|muito legal|gostei|adorei|amei|voce (e|eh) (muito )?(legal|inteligente|bom|otimo|incrivel|esperto|util|demais|top|show)|ficou (otimo|legal|bom|top)|que (legal|bacana|top)|excelente|perfeito|show de bola)\b", [
        "Muito obrigado! Fico feliz que esteja sendo útil.",
        "Que bom que gostou! Pode contar comigo.",
        "Obrigado pelo elogio. Se tiver sugestões, passe para a equipe responsável pelo sistema.",
    ]),
    ("xingamento", r"\b(burro|idiota|inutil|lixo|droga|porcaria|imbecil|estupido|besta|ridiculo|pessimo|horrivel|nao serve pra nada|nao presta)\b", [
        "Desculpe se não ajudei como esperava. Pode me dizer o que você precisa? Vou tentar de outro jeito.",
        "Entendo a frustração. Me conta melhor o que você quer fazer que eu tento resolver.",
    ]),
    ("risada", r"^\s*(k{2,}|(ha){2,}h?|(he){2,}|(hi){2,}|rs+|(rs){2,}|kkk+|aff+|lol|rsrs+|ha+h+a*)\s*$", [
        "Que bom que achou graça!",
        "Hehe. Quer ouvir outra piada?",
        "Rir faz bem. Posso ajudar em algo mais?",
    ]),
    ("desculpa", r"\b(desculpa|desculpe|me perdoa|foi mal|perdao|sinto muito)\b", [
        "Sem problema nenhum! Pode seguir.",
        "Tudo bem, não precisa se desculpar.",
    ]),
    ("nao_entendi", r"\b(nao entendi|nao compreendi|nao ficou claro|explica melhor|explique melhor|como assim|nao captei|pode explicar|repete melhor|ficou confuso|confuso)\b", [
        "Posso explicar de outro jeito. Sobre o que você ficou com dúvida?",
        "Desculpe, vou tentar ser mais claro. Qual parte não ficou clara?",
    ]),
    ("repetir", r"\b(repete|repita|de novo|fala de novo|pode repetir|diz de novo|mais uma vez|como\s*\?)\b", None),
    ("teste", r"^\s*(teste|testando|alo|alô|ola ola|ping|esta ai|ta ai|voce esta ai|tem alguem|alguem ai|funciona)\s*[?!.]*\s*$", [
        "Estou aqui e funcionando! Pode perguntar.",
        "Tudo certo, estou ouvindo. Em que posso ajudar?",
    ]),
    ("sim_solto", r"^\s*(sim|claro|com certeza|pode|isso|aham|uhum|positivo|isso mesmo|exato|certo|beleza|blz|ok|okay|entendi|show|legal|perfeito|ta bom|tudo bem|combinado|fechado|massa|boa)\s*[.!]*\s*$", [
        "Certo! Mais alguma coisa em que eu possa ajudar?",
        "Combinado. Se quiser saber mais algo, é só perguntar.",
        "Ótimo! Estou à disposição.",
    ]),
    ("nao_solto", r"^\s*(nao|nao obrigado|nao precisa|deixa|deixa pra la|esquece|nada|nada nao|agora nao|depois|por enquanto nao|nope)\s*[.!]*\s*$", [
        "Tudo bem! Se mudar de ideia, é só falar.",
        "Sem problema. Estou por aqui se precisar.",
    ]),
    ("fim_de_semana", r"\b(bom fim de semana|bom final de semana|boa semana|bom feriado|bom descanso)\b", [
        "Para você também! Aproveite e descanse.",
        "Obrigado! Que seja uma semana leve para você.",
    ]),
    ("felicitacoes", r"\b(feliz (natal|ano novo|aniversario|pascoa|dia dos professores|dia das maes|dia dos pais|dia do professor)|parabens pelo dia|feliz dia)\b", [
        "Muito obrigado! Para você também, com tudo de bom.",
        "Que carinho! Desejo o mesmo para você.",
    ]),
    ("boa_sorte", r"\b(boa sorte|bons estudos|bom trabalho|boa aula|bom plantao)\b", [
        "Obrigado! Com o inventário em dia, tudo flui melhor.",
        "Valeu! Para você também.",
    ]),
    ("fome_sono", r"\b(estou|to|tou) com (fome|sono|calor|frio|dor de cabeca)\b", [
        "Então vale uma pausa! Uma água, um café ou um lanche e você volta com tudo.",
        "Cuide-se um pouco. O inventário espera, e eu também.",
    ]),
    ("carinho", r"\b(te amo|gosto de voce|amo voce|voce e meu amigo|voce e demais)\b", [
        "Que carinho! Fico feliz em ajudar.",
        "Obrigado! Também gosto de trabalhar com você.",
    ]),
    ("me_entende", r"\b(voce me entende|voce me ouve|voce entende portugues|voce entende o que eu falo|voce fala portugues)\b", [
        "Entendo bastante do sistema e dos equipamentos, e falo português do Brasil. Se algo escapar, tento sugerir o que fazer.",
    ]),
    ("de_onde", r"\b(de onde (voce|vc) (e|eh)|onde (voce|vc) mora|onde voce vive|voce mora onde)\b", [
        "Moro no servidor do sistema, sem endereço e sem trânsito. Atendo a {escola} de onde estiver.",
    ]),
    ("lembra_de_mim", r"\b(voce (lembra|se lembra) de mim|voce me conhece|ja conversamos)\b", [
        "Lembro do que conversamos nesta sessão. Ao atualizar a página, começo uma conversa nova.",
    ]),
    ("recomecar", r"\b(limpar (a )?conversa|apagar (a )?conversa|comecar de novo|recomecar|esquece tudo|zerar conversa|nova conversa)\b", [
        "Para começar uma conversa nova, atualize a página. Enquanto isso, pode perguntar à vontade.",
    ]),
    ("ajuda_geral", r"(^\s*(ajuda|help|socorro|duvida|ajudar)\s*[?!.]*\s*$|\b(preciso de (uma )?ajuda|me ajuda|me ajude|pode me ajudar|voce pode me ajudar|tenho uma duvida|tenho uma pergunta|posso perguntar|queria perguntar|quero ajuda)\b)", [
        "Claro! Pode perguntar. Consigo tirar dúvidas de uso, contar e listar equipamentos, mostrar o que mudou e até conversar um pouco. Qual é a sua dúvida?",
        "Estou aqui para isso. Me diga o que você precisa, por exemplo: quantos notebooks existem, onde está um equipamento ou como cadastrar.",
    ]),
    ("entediado", r"\b(estou|to|tou) (entediad[oa]|com tedio|sem nada pra fazer|de boa sem fazer nada)\b|\b(me entretem|me distrai|me anima|conversa comigo|vamos conversar|bater papo|quer conversar)\b", [
        "Então vamos de leve: quer uma piada ou uma curiosidade? É só pedir.",
        "Posso contar uma curiosidade, uma piada ou fazer uma conta de cabeça. Qual você prefere?",
    ]),
    ("concorrentes", r"\b(chatgpt|gemini|alexa|siri|google assistente|copilot|bard|claude)\b", [
        "Sou bem mais simples que esses: conheço apenas o Ativos Escolares e os equipamentos da {escola}. Mas nisso eu me saio bem.",
    ]),
    ("clima", r"\b(clima|previsao do tempo|vai chover|esta chovendo|temperatura|faz calor|faz frio|esta frio|esta calor)\b", [
        "Não consigo ver o tempo lá fora: funciono sem internet. Mas se quiser saber das condições dos equipamentos, é comigo mesmo.",
    ]),
    ("fora_do_tema", r"\b(futebol|jogo do|placar|campeonato|novela|filme|serie de tv|musica|cantor|politica|eleicao|noticia|noticias|dolar|bolsa de valores|horoscopo|signo|receita de|capital d[aeo]|presidente d[aeo]|quem descobriu|quem inventou|historia d[aeo]|quantos habitantes|tabuada)\b", [
        "Isso foge do que eu sei: funciono offline e só conheço o sistema e os equipamentos da escola. Se quiser, conto uma piada ou uma curiosidade para descontrair.",
        "Não tenho como responder isso, porque não acesso a internet nem conhecimentos gerais. Posso ajudar com os equipamentos, com o uso do sistema ou com uma conversa leve.",
    ]),
    ("escola_nome", r"\b(qual (e )?o nome da escola|nome da escola|que escola (e|eh) (essa|esta|essa aqui)|em qual escola|de qual escola)\b", [
        "O sistema é da {escola}.",
    ]),
    ("escola_dados", r"\b(onde fica a escola|endereco da escola|telefone da escola|diretor|diretora|quantos alunos|quantos professores|quantas turmas|horario das aulas|e-?mail da escola)\b", [
        "Esse dado eu não tenho: só conheço os equipamentos cadastrados no Ativos Escolares da {escola}. Quer ver o resumo deles?",
    ]),
    ("capacidades", r"(o que (voce|vc) (sabe|pode|faz|consegue|responde|entende)|para que (voce )?serve|pra que (voce )?serve|como (voce|vc) funciona|(voce|vc) faz o que|que (voce|vc) sabe fazer|me ajuda com o que|do que (voce|vc) (e|eh) capaz|quais sao suas funcoes|seus recursos|o que da pra perguntar|o que posso perguntar|o que eu posso (te )?perguntar|comandos)", None),
]

# Respostas especiais montadas pelo motor (precisam de dados)
CAPACIDADES = (
    "Posso ajudar de várias formas:\n"
    "• **Contar e listar** equipamentos (por tipo, local, categoria, marca, situação ou responsável)\n"
    "• **Achar um equipamento** pelo ID e dizer onde está, quem usa e como está\n"
    "• **Comparar e ranquear** (qual local tem mais, qual marca predomina)\n"
    "• **Mostrar o que mudou** no histórico\n"
    "• **Explicar o sistema**: cadastrar, editar, exportar, QR Code, filtros...\n"
    "• **Conversar**: piadas, curiosidades, contas simples, data e hora\n"
    "É só perguntar do seu jeito."
)

PIADAS = [
    "Por que o computador foi ao médico? Porque estava com vírus.",
    "O que o Wi-Fi disse para o notebook? \"Sem você eu perco a conexão.\"",
    "Por que o programador confunde Halloween com Natal? Porque 31 de outubro é igual a 25 de dezembro (em octal, é claro).",
    "O que o aluno de informática responde quando o professor manda salvar o arquivo? \"Já salvei... só não lembro onde.\"",
    "Por que a planilha nunca se perde? Porque sempre sabe em qual linha e em qual coluna está.",
    "O que a impressora disse para o papel? \"Você sempre trava quando eu mais preciso.\"",
    "Por que o notebook ficou na sala o dia todo? Porque estava de bateria carregada e sem pressa.",
    "Qual é o café preferido do programador? O Java.",
    "Por que o tablet foi promovido? Porque sempre dá conta de tudo com um toque.",
    "O que um inventário diz para o outro? \"Pelo menos aqui todo mundo está contado.\"",
]

CURIOSIDADES = [
    "O QR Code foi criado em 1994 por uma empresa japonesa, a Denso Wave, para rastrear peças na produção de automóveis.",
    "O primeiro mouse de computador, desenvolvido por Douglas Engelbart nos anos 1960, tinha a carcaça de madeira.",
    "O e-mail é mais antigo que a web: a primeira mensagem entre computadores diferentes foi enviada em 1971, e foi nessa época que o @ passou a separar o nome do usuário do servidor.",
    "Uma das histórias mais famosas sobre a palavra \"bug\" conta que, em 1947, uma mariposa travou um computador na Universidade de Harvard e foi colada no caderno de registros da equipe.",
    "\"Wi-Fi\" não é abreviação de nada: é apenas um nome comercial escolhido para a tecnologia.",
    "Em 1956, o IBM 305 RAMAC guardava cerca de 5 megabytes em um conjunto de discos que ocupava um móvel enorme e pesava mais de uma tonelada.",
    "O primeiro site do mundo foi publicado em 1991, por Tim Berners-Lee, no CERN. Ele explicava o que era a própria web.",
    "A palavra \"pixel\" vem de \"picture element\", ou elemento de imagem.",
    "Os primeiros computadores pessoais não tinham disco rígido: os programas ficavam em fitas ou disquetes.",
    "Os códigos de barras e os QR Codes funcionam mesmo com uma parte danificada, porque guardam informação extra para corrigir erros de leitura.",
]

MOTIVACAO = [
    "Organização é uma forma de cuidado: cada equipamento no lugar certo é uma aula que acontece sem imprevistos. Você está fazendo um bom trabalho.",
    "Pequenos registros de hoje evitam grandes buscas amanhã. Continue assim.",
    "Um passo de cada vez. Inventário em dia é conquista, mesmo quando parece rotina.",
    "Quem cuida do que é da escola cuida de todos que usam. Obrigado pelo esforço.",
    "Respire fundo, tome uma água e siga. O que está difícil agora fica mais leve com um pouco de organização.",
]

DICAS = [
    "Dica: confira o inventário uma vez por mês e compare com o que está nas salas. Diferenças pequenas viram problemas grandes se ninguém olha.",
    "Dica: mantenha a etiqueta com o QR Code colada em um lugar fácil de ver, em todo equipamento. Ela agiliza qualquer consulta.",
    "Dica: exporte a planilha de tempos em tempos e guarde uma cópia. É o seu backup mais simples.",
    "Dica: sempre que um equipamento mudar de sala, edite o local no mesmo dia. O histórico registra a mudança e evita confusão depois.",
    "Dica: marque como crítico o que não pode faltar nas aulas. Assim o painel mostra o que merece atenção primeiro.",
    "Dica: use senhas longas e diferentes para cada administrador, e troque quando alguém deixar a equipe.",
]

# Ajuda do sistema ----------------------------------------------------------

# chaves: expressões já normalizadas. resposta: texto. ir: (tela, rótulo do botão).
# somente_admin: acrescenta um aviso quando quem pergunta é visitante.
AJUDA = [
    {"id": "cadastrar", "chaves": ("cadastrar", "cadastro", "registrar", "adicionar", "novo ativo", "incluir", "criar equipamento", "novo equipamento", "colocar equipamento"),
     "resposta": "Para cadastrar, abra o **Inventário** e clique em **Novo ativo**. Preencha categoria, tipo, ID, marca, modelo, local, situação e criticidade (responsáveis, carregador e mochila são opcionais) e clique em **Cadastrar**. O sistema avisa se o ID já existir naquela categoria.",
     "ir": ("inventario", "Abrir Inventário"), "somente_admin": True},
    {"id": "editar", "chaves": ("editar", "alterar", "atualizar", "modificar", "mudar dados", "corrigir", "trocar o local", "mudar de sala", "mudar o local", "trocar responsavel"),
     "resposta": "Para editar, abra o equipamento no **Inventário** (clicando na linha ou no lápis) e use **Editar**. Altere o que precisar e salve: cada mudança fica registrada no **Histórico**, com o valor antigo e o novo.",
     "ir": ("inventario", "Abrir Inventário"), "somente_admin": True},
    {"id": "excluir", "chaves": ("excluir", "remover", "apagar", "deletar", "tirar equipamento", "dar baixa", "baixa de equipamento"),
     "resposta": "Para excluir, abra o equipamento e clique em **Excluir**. O sistema pede confirmação antes. A exclusão não pode ser desfeita, mas o registro dela fica no **Histórico**.",
     "ir": ("inventario", "Abrir Inventário"), "somente_admin": True},
    {"id": "desfazer", "chaves": ("desfazer", "recuperar equipamento", "restaurar", "voltar atras", "excluir sem querer", "apaguei sem querer", "excluido sem querer", "apagado sem querer", "recuperar o que apaguei"),
     "resposta": "A exclusão não pode ser desfeita pelo sistema. Mas o **Histórico** guarda o que era o equipamento, então dá para cadastrar de novo com os mesmos dados.",
     "ir": ("historico", "Abrir Histórico")},
    {"id": "exportar", "chaves": ("exportar", "excel", "planilha", "xlsx", "baixar tabela", "relatorio", "baixar dados", "gerar relatorio", "baixar lista", "imprimir lista", "imprimir relatorio", "baixar a tabela", "baixar tabela", "salvar em excel", "tabela dos equipamentos", "baixar os equipamentos", "tirar relatorio", "lista em excel"),
     "resposta": "Para exportar, vá em **Administração** (ou use o botão no **Inventário**) e clique em **Exportar Excel**. O arquivo relatorio_ativos.xlsx traz todos os equipamentos, com filtro ativado e pronto para imprimir em paisagem, com o nome da escola no cabeçalho.",
     "ir": ("admin", "Abrir Administração"), "somente_admin": True},
    {"id": "importar", "chaves": ("importar", "importacao", "subir planilha", "atualizar a planilha", "dados.xlsx", "carregar planilha", "enviar planilha"),
     "resposta": "A importação da planilha Dados.xlsx é feita pelo servidor (programa import_excel.py), não por uma tela. Ela adiciona os equipamentos novos e atualiza os existentes. Atenção: edições feitas pelo site em equipamentos que vieram da planilha podem voltar ao valor do Excel quando o servidor reinicia."},
    {"id": "painel", "chaves": ("painel", "dashboard", "tela inicial", "pagina inicial", "inicio"),
     "resposta": "O **Painel** é a visão geral: total de ativos, em uso, não em uso e críticos, mais gráficos por situação, tipo, local e categoria e a lista das últimas alterações. Clicar em um indicador abre o Inventário já filtrado.",
     "ir": ("dashboard", "Abrir Painel")},
    {"id": "estatisticas", "chaves": ("estatistica", "estatisticas", "grafico", "graficos", "percentual", "percentuais", "ranking"),
     "resposta": "A página **Estatísticas** mostra percentuais de uso, não uso e críticos, rankings por tipo e por local, a distribuição por categoria e os três locais e tipos mais comuns.",
     "ir": ("estatisticas", "Abrir Estatísticas")},
    {"id": "crud", "chaves": ("crud",),
     "resposta": "CRUD são as quatro operações básicas de um sistema de dados: **C**riar (cadastrar), **R**ead (consultar), **U**pdate (editar) e **D**elete (excluir). Aqui, administradores fazem as quatro e visitantes só consultam."},
    {"id": "critico", "chaves": ("critico", "criticos", "criticidade", "equipamento critico"),
     "resposta": "**Equipamento crítico** é o que não pode faltar ou ficar parado sem atrapalhar as atividades. Ele é marcado com criticidade \"Sim\" e aparece em destaque no Painel. Dá para filtrar por criticidade no Inventário.",
     "ir": ("inventario", "Abrir Inventário")},
    {"id": "historico", "chaves": ("historico", "auditoria", "log de alteracoes", "registro de alteracoes"),
     "resposta": "O **Histórico** registra cada cadastro, edição e exclusão: quem fez, quando, qual campo mudou, o valor antigo e o novo. Você pode ver tudo na página Histórico ou só o de um equipamento, na aba Histórico dele.",
     "ir": ("historico", "Abrir Histórico")},
    {"id": "qr", "chaves": ("qr", "qrcode", "qr code", "etiqueta", "plaquinha", "plaqueta", "imprimir etiqueta", "codigo qr", "ler qr", "escanear"),
     "resposta": "Cada equipamento tem um **QR Code**. Abra o equipamento e vá na aba **QR Code** para ver, baixar em PNG ou imprimir a etiqueta (com o nome da escola, o ID e a descrição). Ao escanear com o celular, o sistema abre os detalhes daquele equipamento; se a pessoa não estiver logada, ele pede o login primeiro.",
     "ir": ("inventario", "Abrir Inventário")},
    {"id": "busca", "chaves": ("buscar", "busca", "pesquisar", "pesquisa", "procurar", "achar", "encontrar equipamento", "localizar"),
     "resposta": "No **Inventário**, use o campo de busca: ele procura em ID, responsável, marca, modelo, local e outros campos, ignora acentos e aceita várias palavras (por exemplo, \"positivo sala maker\"). Digitar \"em uso\" ou \"não em uso\" filtra pela situação.",
     "ir": ("inventario", "Abrir Inventário")},
    {"id": "filtros", "chaves": ("filtro", "filtros", "filtrar", "mostrar so", "ver apenas"),
     "resposta": "No **Inventário**, clique em **Filtros** para abrir o painel: categoria, tipo, local, situação, criticidade e mochila, que podem ser combinados com a busca. Os filtros ligados aparecem como etiquetas ao lado da busca, e cada uma pode ser removida com um clique.",
     "ir": ("inventario", "Abrir Inventário")},
    {"id": "ordenar", "chaves": ("ordenar", "ordenacao", "classificar", "organizar a lista", "ordem alfabetica", "colocar em ordem"),
     "resposta": "Para ordenar, clique no título de uma coluna do Inventário (um novo clique inverte a ordem) ou use a seção **Ordenação** dentro do painel **Filtros**, que também funciona no celular.",
     "ir": ("inventario", "Abrir Inventário")},
    {"id": "paginas", "chaves": ("paginacao", "proxima pagina", "pagina seguinte", "ver mais equipamentos", "muitos equipamentos", "passar de pagina"),
     "resposta": "O Inventário mostra 15 equipamentos por vez. Use **Anterior** e **Próxima**, no fim da lista, para navegar."},
    {"id": "visitante", "chaves": ("visitante", "modo consulta", "somente leitura", "entrar sem senha", "entrar como visitante", "sem login"),
     "resposta": "O **visitante** entra pelo botão \"Entrar como visitante\", sem senha. Ele consulta tudo (painel, estatísticas, inventário, detalhes, histórico e QR Code), mas não pode cadastrar, editar, excluir nem exportar."},
    {"id": "permissoes", "chaves": ("permissao", "permissoes", "quem pode", "pode editar", "pode excluir", "perfil", "perfis", "administrador", "admin"),
     "resposta": "Existem dois perfis. **Administradores** têm acesso total (cadastrar, editar, excluir, exportar e ver a página Administração). **Visitantes** só consultam. As permissões são conferidas no servidor, então não dá para burlar escondendo ou mostrando botões."},
    {"id": "situacao", "chaves": ("situacao", "em uso", "nao em uso", "fora de uso", "disponivel"),
     "resposta": "A **situação** diz se o equipamento está **Em uso** ou **Não em uso** (guardado ou disponível). Dá para filtrar por ela no Inventário e ver o total no Painel.",
     "ir": ("dashboard", "Abrir Painel")},
    {"id": "tema", "chaves": ("tema escuro", "modo escuro", "tema claro", "modo claro", "dark mode", "escurecer", "mudar a cor", "mudar cor", "fundo escuro", "cores do site"),
     "resposta": "Para trocar entre o tema claro e o escuro, clique no ícone de **lua/sol** no canto superior direito. O sistema lembra da sua escolha neste aparelho."},
    {"id": "celular", "chaves": ("celular", "mobile", "telefone", "smartphone", "no celular", "no tablet", "responsivo"),
     "resposta": "O sistema funciona no celular. No Inventário a tabela vira cartões, o menu abre pelo ícone de três linhas e o QR Code pode ser escaneado direto pela câmera."},
    {"id": "senha", "chaves": ("esqueci a senha", "esqueci minha senha", "trocar senha", "mudar senha", "alterar senha", "redefinir senha", "recuperar senha", "perdi a senha", "senha errada", "qual a senha", "minha senha"),
     "resposta": "As senhas dos administradores são definidas na configuração do servidor (variável ADMIN_USERS), não pelo sistema. Se esqueceu a sua ou quer trocá-la, peça a quem cuida do servidor para atualizar. Enquanto isso, você pode entrar como visitante para consultar."},
    {"id": "login", "chaves": ("login", "logar", "como entrar", "fazer login", "sair", "logout", "sessao", "sessao expirou", "caiu o login", "deslogou", "desconectou"),
     "resposta": "Na tela de login, use usuário e senha de administrador ou o botão de visitante. A sessão dura 8 horas; depois disso o sistema avisa e volta ao login. Para sair, use **Sair** no menu lateral. Após várias senhas erradas, o acesso fica bloqueado por alguns minutos."},
    {"id": "erro", "chaves": ("nao consigo", "nao funciona", "deu erro", "erro", "bug", "travou", "nao aparece", "nao abre", "nao carrega", "problema", "nao salva", "nao deixa", "nao aparece o botao", "sumiu o botao"),
     "resposta": "Vamos tentar resolver. Algumas causas comuns: (1) você está como **visitante**, e só administradores cadastram, editam, excluem e exportam; (2) a **sessão expirou**, então saia e entre de novo; (3) o ID já existe naquela categoria; (4) falta algum campo obrigatório no formulário. Me conta o que aconteceu exatamente que eu ajudo."},
    {"id": "backup", "chaves": ("backup", "copia de seguranca", "salvar os dados", "perder dados", "perder os dados", "dados somem", "seguranca dos dados", "guardar os dados"),
     "resposta": "Para ter uma cópia de segurança, exporte o Excel de tempos em tempos e guarde o arquivo, e mantenha também cópias do arquivo do banco (ativos.db). Em hospedagem na nuvem, confirme com quem cuida do servidor se o banco fica em armazenamento permanente."},
    {"id": "assistente", "chaves": ("assistente", "chatbot", "chat", "robo", "falar com voce", "conversar com voce"),
     "resposta": "Eu sou o assistente do sistema. Respondo dúvidas de uso, conto e listo equipamentos, mostro o que mudou, e também converso um pouco. Pergunte do seu jeito; se eu não entender, tento sugerir o que você pode ter querido dizer."},
    {"id": "atalhos", "chaves": ("atalho", "atalhos", "teclado", "tecla", "esc fecha", "fechar janela"),
     "resposta": "Alguns atalhos: **Esc** fecha janelas, o assistente e o menu do celular; **Enter** abre o equipamento quando uma linha da tabela está selecionada; **Tab** navega pelos campos."},
    {"id": "mochila", "chaves": ("mochila", "bolsa do notebook", "campo mochila"),
     "resposta": "**Mochila** indica se o equipamento tem uma mochila ou bolsa de transporte (Sim, Não ou Não se aplica, como nas televisões). Dá para filtrar por esse campo no Inventário."},
    {"id": "carregador", "chaves": ("carregador", "campo carregador", "fonte do notebook"),
     "resposta": "**Carregador** registra se o equipamento tem carregador e, quando existe, o número dele (por exemplo, \"Sim / 25\"). É um campo opcional."},
    {"id": "categorias", "chaves": ("categoria", "categorias", "grupos", "grupo de equipamentos", "divisao dos equipamentos"),
     "resposta": "As **categorias** organizam os equipamentos por grupo: 2º Ano (2A), 3º Ano (3A), Setups, Carrinhos, Tablets e Televisão. A categoria aparece em cada linha do Inventário e há botões para filtrar por ela.",
     "ir": ("inventario", "Abrir Inventário")},
    {"id": "ids", "chaves": ("id do equipamento", "numero do equipamento", "patrimonio", "numero de patrimonio", "n/", "id repetido", "id com n", "o que e o id"),
     "resposta": "O **ID** é o número da plaquinha do equipamento. O mesmo número pode existir em categorias diferentes (por exemplo, no 2A e nos Carrinhos). Equipamentos sem número na planilha aparecem como N/, N/-2, N/-3 e assim por diante."},
    {"id": "duplicado", "chaves": ("duplicado", "ja existe", "repetido", "mesmo id", "id repetido", "dois equipamentos iguais"),
     "resposta": "O sistema não permite dois equipamentos com o mesmo ID na mesma categoria. Se aparecer \"já existe\", confira o ID e a categoria, ou pesquise o ID no Inventário para ver o que já está cadastrado.",
     "ir": ("inventario", "Abrir Inventário")},
    {"id": "offline", "chaves": ("internet", "offline", "sem internet", "precisa de internet", "conexao", "funciona sem internet"),
     "resposta": "O sistema usa apenas recursos próprios: gráficos, QR Codes, ícones e fontes funcionam sem depender de serviços externos. Eu mesmo funciono offline, por regras e consultando o banco de dados."},
    {"id": "lento", "chaves": ("lento", "demora", "devagar", "travando", "lag", "pesado", "demorando"),
     "resposta": "Se o sistema estiver lento, tente atualizar a página e fechar abas que não estiver usando. O sistema foi otimizado para celular e computador, então se a lentidão continuar, avise quem cuida do servidor: pode ser a conexão ou o serviço de hospedagem."},
    {"id": "seguranca", "chaves": ("seguro", "seguranca", "protegido", "privacidade", "dados pessoais", "lgpd", "hacker", "invadir"),
     "resposta": "O sistema confere as permissões no servidor, guarda as senhas de forma protegida, limita tentativas de login, trata tudo o que é digitado como texto comum (sem executar) e usa cabeçalhos de segurança. Mesmo assim, troque as senhas padrão e mantenha backups."},
    {"id": "detalhes", "chaves": ("detalhes", "abrir equipamento", "ver equipamento", "ver os dados do equipamento", "informacoes do equipamento"),
     "resposta": "No Inventário, clique na linha de um equipamento para abrir os **detalhes**. A janela tem três abas: Detalhes, QR Code e Histórico. Administradores também veem os botões Editar e Excluir.",
     "ir": ("inventario", "Abrir Inventário")},
    {"id": "administracao", "chaves": ("administracao", "configuracoes", "configuracao", "pagina de administracao"),
     "resposta": "A página **Administração** é só para administradores: tem a exportação do Excel, informações do sistema (escola, quantidade de equipamentos, tamanho do banco), a lista de contas e orientações de segurança.",
     "ir": ("admin", "Abrir Administração"), "somente_admin": True},
    {"id": "comecar", "chaves": ("como usar", "tutorial", "primeiros passos", "por onde comeco", "como funciona o sistema", "para que serve o sistema", "como comecar", "como usar o sistema", "explica o sistema", "o que e este sistema", "o que e esse sistema", "o que e o sistema", "me ensina a usar"),
     "resposta": "Começando: o **Painel** dá a visão geral; o **Inventário** é onde você busca, filtra e abre cada equipamento (com QR Code e histórico); as **Estatísticas** aprofundam os números; o **Histórico** mostra o que mudou; e a **Administração** (só admins) exporta o Excel. Quer que eu detalhe alguma dessas telas?"},
    {"id": "usuarios", "chaves": ("criar usuario", "novo usuario", "adicionar usuario", "novo administrador", "cadastrar usuario", "gerenciar usuarios"),
     "resposta": "O cadastro de usuários pelo sistema ainda não existe. Os administradores são definidos na configuração do servidor (variável ADMIN_USERS). Para incluir alguém, peça a quem cuida do servidor."},
    {"id": "responsavel_campo", "chaves": ("campo responsavel", "o que e responsavel", "quem e o responsavel", "responsavel 1", "responsavel 2"),
     "resposta": "**Responsável 1 e 2** são as pessoas que usam ou cuidam do equipamento (alunos, professores ou grupos, como \"Professores\"). São campos opcionais."},
]

# Glossário (perguntas como "o que é um backup?") ---------------------------
GLOSSARIO = [
    (("notebook", "notebooks", "laptop"), "Notebook é um computador portátil, com tela, teclado e bateria no mesmo aparelho."),
    (("tablet", "tablets"), "Tablet é um aparelho portátil de tela sensível ao toque, parecido com um celular grande."),
    (("setup", "setups"), "No inventário, **setup** é o conjunto de computador de mesa e periféricos (monitor, teclado, mouse) montado em um local."),
    (("televisao", "tv", "televisor"), "Televisão, aqui no sistema, é a TV usada para apresentações e aulas nas salas."),
    (("patrimonio",), "Patrimônio é o conjunto de bens da escola, como equipamentos e móveis. A plaquinha com número identifica cada bem."),
    (("inventario",), "Inventário é a lista organizada de todos os bens, com onde estão, quem usa e em que situação se encontram."),
    (("backup",), "Backup é uma cópia de segurança dos dados, guardada em outro lugar, para recuperar tudo se algo der errado."),
    (("login",), "Login é a entrada no sistema com usuário e senha, que confirma quem você é e o que pode fazer."),
    (("sessao",), "Sessão é o período em que você fica conectado ao sistema depois do login. Aqui ela dura 8 horas."),
    (("senha forte", "senha segura"), "Uma senha forte é longa (de preferência 12 caracteres ou mais), mistura letras, números e símbolos e não usa dados óbvios, como datas de aniversário."),
    (("senha",), "Senha é o código secreto que comprova que você é você. Não compartilhe e evite usar a mesma em vários lugares."),
    (("banco de dados",), "Banco de dados é onde o sistema guarda as informações de forma organizada. Aqui, é o arquivo ativos.db."),
    (("planilha", "excel", "xlsx"), "Planilha é uma tabela de linhas e colunas, como as do Excel. O sistema exporta os equipamentos nesse formato."),
    (("qr code", "qrcode"), "QR Code é um código de barras em formato de quadrado que o celular lê pela câmera. Aqui ele leva direto ao equipamento."),
    (("wifi", "wi-fi"), "Wi-Fi é a tecnologia que conecta aparelhos à internet sem cabo."),
    (("nuvem",), "Nuvem é o armazenamento e processamento em servidores na internet, em vez de no seu próprio computador."),
    (("sistema operacional",), "Sistema operacional é o programa principal do computador, como Windows, Linux ou Android, que faz tudo o mais funcionar."),
    (("bateria",), "Bateria é o que permite usar o equipamento sem ligá-lo na tomada. Com o tempo, ela perde capacidade."),
    (("carregador",), "Carregador é a fonte que liga o equipamento à tomada e recarrega a bateria."),
    (("monitor",), "Monitor é a tela que mostra a imagem do computador de mesa."),
    (("mouse",), "Mouse é o aparelho que move o cursor na tela e permite clicar."),
    (("roteador", "router"), "Roteador é o aparelho que distribui a internet para os dispositivos, por cabo ou Wi-Fi."),
    (("ativo", "ativos"), "Ativo, aqui, é cada equipamento cadastrado no inventário da escola."),
    (("criticidade",), "Criticidade indica o quanto um equipamento é importante: os críticos não podem faltar ou ficar parados."),
    (("categoria",), "Categoria é o grupo do equipamento: 2A, 3A, Setups, Carrinhos, Tablets ou Televisão."),
    (("cache",), "Cache é uma memória temporária que guarda arquivos para o site carregar mais rápido nas próximas vezes."),
    (("hardware",), "Hardware é a parte física do computador: peças, tela, teclado, bateria."),
    (("software",), "Software é a parte lógica: os programas e o sistema que rodam no hardware."),
    (("virus",), "Vírus é um programa malicioso que se espalha e pode danificar ou roubar dados. Antivírus e cuidado com anexos ajudam a evitar."),
    (("firewall",), "Firewall é uma barreira que filtra o tráfego de rede e bloqueia acessos indevidos."),
    (("servidor",), "Servidor é o computador (geralmente na internet) que guarda o sistema e responde aos pedidos dos usuários."),
    (("api",), "API é um jeito de um programa conversar com outro, trocando informações de forma padronizada."),
]
