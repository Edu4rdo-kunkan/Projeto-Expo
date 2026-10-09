O site Ativos Escolares é formado por vários arquivos, e cada um tem uma função para o sistema funcionar.

- `Dados.xlsx`: é a planilha com as informações dos equipamentos da escola.
- `import_excel.py`: lê a planilha e passa as informações para o sistema.
- `ativos.db`: é o arquivo que guarda os dados dos equipamentos e o histórico das mudanças.
- `app.py`: faz o site funcionar e controla o acesso dos usuários.
- `assistente.py` e `assistente_conteudo.py`: fazem o assistente virtual funcionar e responder às perguntas.
- `templates/`: contém os arquivos das páginas do site.
- `static/css/` e `static/js/`: cuidam da aparência do site e das funções dos botões, gráficos, filtros e QR Codes.
- `tests/`: contém arquivos que testam se o sistema está funcionando corretamente.
- `backup_original/`: guarda cópias dos arquivos antigos.
- `docs/capturas/`: guarda imagens das telas do site.

Como tudo funciona: a planilha fornece as informações, o arquivo `import_excel.py` coloca esses dados no banco de dados `ativos.db`, e o arquivo `app.py` usa essas informações para mostrar tudo no site.

Assim, o administrador pode cadastrar, editar, excluir e consultar os equipamentos. É importante guardar cópias de segurança para não perder os dados.

Criadores: Eduardo A. 99,99% / Saymon M. 00,01% / Ronaldo B. 00,00% / Matheus M. 00,00% / Yasmin C. 00,00%
