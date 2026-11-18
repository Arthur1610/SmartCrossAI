# SMARTCROSS AI

**Mobilidade Urbana Inteligente · Global Solution FIAP**

O SmartCross AI investiga como a visão computacional pode informar uma faixa de pedestres com iluminação complementar. O protótipo confirma presença na zona de espera e aciona LEDs virtuais. A demonstração funciona em um PC Windows sem webcam e usa YOLOv8n para analisar vídeo em CPU quando uma fonte real está disponível.

O projeto é acadêmico. A ROI indica presença em uma área configurada. A iluminação virtual não autoriza a travessia. O software não controla sinalização real e não possui certificação de segurança.

## Instalação no Windows

Use Python 3.11 ou superior de 64 bits no PATH. Execute a partir da pasta do projeto no PowerShell.

```powershell
.\instalar.bat --simulacao
.\iniciar.bat
```

Abra [o dashboard local](http://127.0.0.1:5000). Use Ctrl+C no terminal para sair. A variante de simulação instala Flask e Pytest. Para webcam e vídeo, execute `.\instalar.bat` no mesmo ambiente. O instalador completo baixa PyTorch para CPU, OpenCV e Ultralytics.

Instalação completa manual pelo PowerShell, sem precisar ativar o ambiente virtual.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Ao trocar de computador, transfira os arquivos do repositório e execute a instalação novamente para recriar a `.venv`. A primeira análise real pode baixar `yolov8n.pt` dos releases oficiais da Ultralytics para `runtime/models/`. Depois do download, a inferência usa os pesos locais em CPU, sem credenciais ou serviços de detecção. [Documentação do YOLOv8](https://docs.ultralytics.com/models/yolov8/) · [Instalação oficial do PyTorch](https://pytorch.org/get-started/locally/)

## Demonstração sem webcam

1. Selecione **Simulação** e clique em **Iniciar análise**.
2. Selecione **2** em **Pessoas na zona**. Observe **DETECÇÃO**, seguida de **ATIVA**, e os LEDs acesos.
3. Volte a **0**. Os LEDs permanecem acesos durante **AGUARDANDO DESATIVAÇÃO** e depois apagam.
4. Mostre o gráfico, os eventos e a contagem de ativações.
5. Altere a posição ou as dimensões da ROI e observe a cena virtual. A simulação exibe presença gerada pelo controle e mantém FPS de IA em branco.

## Webcam e vídeo

No notebook, instale o conjunto completo e permita que aplicativos de desktop acessem a câmera nas configurações de privacidade do Windows. Selecione **Webcam** e tente o índice 0. Troque o índice se houver outra câmera. Clique em **Parar**, aguarde a interrupção e inicie novamente para reiniciar a captura.

Para **Vídeo local**, selecione um MP4 autorizado com até 200 MiB e inicie. O vídeo pode ser reiniciado do começo pela mesma seleção. O arquivo recebido usa uma cópia temporária durante a sessão para permitir reinícios. A cópia é descartada ao substituir o vídeo, mudar o modo ou encerrar normalmente. Um encerramento forçado pode deixar arquivos temporários no Windows. O histórico guarda somente horário, tipo, fonte e contagem na ROI. Quadros processados são mantidos em memória para o monitor.

A caixa mostra a confiança da detecção e usa cor para distinguir pessoas dentro e fora da zona. A posição usada é o centro inferior da caixa. Os parâmetros da ROI são frações entre 0 e 1, com origem no canto superior esquerdo da imagem. Ajuste a região com base no enquadramento. Configurações do painel duram pela sessão. Eventos e estatísticas sobrevivem ao reinício.

## Arquitetura

```text
Dashboard HTML/CSS/JS
  └─ Flask · API /api · polling e MJPEG
      ├─ Engine · thread de captura ou simulação
      │   ├─ Sources · webcam e MP4 via OpenCV
      │   ├─ Vision · YOLOv8n classe pessoa, ROI e JPEG
      │   └─ Lighting · confirmação e retenção por relógio monotônico
      └─ Events · SQLite e agregação por hora
```

| Método e rota | Função |
| --- | --- |
| GET /api/state | Estado, indicadores e configurações |
| POST /api/source | Seleciona fonte por JSON ou recebe MP4 em campo multipart `video` |
| POST /api/start · POST /api/stop | Inicia ou interrompe a análise |
| GET /api/stream | Quadros processados em MJPEG |
| PATCH /api/settings · PUT /api/roi | Atualiza parâmetros validados |
| POST /api/simulation | Define `count` entre 0 e 5 |
| GET /api/events · GET /api/stats | Histórico e gráfico de 24 horas |

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Os testes usam arquivos temporários, relógio controlado nos testes unitários e o cliente Flask nos testes da API. Nenhum teste requer câmera, GPU, pesos ou acesso à internet.

## Limitações

- O MVP usa uma fonte por vez e identifica variações na contagem da ROI. Ele não atribui identidades para acompanhar pessoas individualmente.
- Iluminação, oclusão e posição da câmera afetam a detecção. O desempenho depende da CPU. Vídeos podem rodar abaixo da cadência original.
- A confirmação e retenção são medidas em tempo de processamento. Parar a fonte, chegar ao fim do vídeo ou perder a captura encerra o estado da faixa virtual.
- O servidor Flask é executado em loopback para demonstração local.

## Capturas de tela

Espaço reservado para capturas do monitor em simulação, da faixa virtual ativa e do histórico. Para o portfólio, use imagens da cena virtual ou material autorizado.

## Roteiro para o pitch

Comece pelo problema e mostre a ROI na cena virtual. Demonstre confirmação, acionamento e retenção. Apresente histórico e gráfico. Use vídeo autorizado ou webcam para mostrar a inferência real e as caixas de detecção. Encerre explicando que uma eventual integração física exigiria projeto de engenharia, validação de segurança, acessibilidade e aprovação da autoridade de trânsito.

## Roadmap

- Avaliar desempenho com vídeos autorizados em diferentes horários e enquadramentos.
- Medir falsos positivos, falsos negativos e latência em cenários de teste.
- Estudar acessibilidade e requisitos de eventual integração física com especialistas.

## Dependências e licenciamento

O código do projeto é disponibilizado sob [AGPL-3.0](LICENSE). A Ultralytics oferece YOLOv8 e seus pesos sob AGPL-3.0 e licença Enterprise. Consulte os termos antes de redistribuir ou integrar em sistemas fechados. Flask e PyTorch usam licenças BSD, OpenCV usa Apache 2.0 e Pytest usa MIT. Consulte também as licenças das dependências transitivas. [Licenciamento Ultralytics](https://www.ultralytics.com/license)
