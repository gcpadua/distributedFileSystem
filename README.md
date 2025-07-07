# distributedFileSystem
Como executar o programa:
1. Execute o serviddor orquestrador com o comando: python .\orchestrator.py
2. Para cada cliente, de o cd para a pasta que sera compartilhada e execute o seguinte comando: python ../clientV5.py --orch http://127.0.0.1:5000 --host localhost --port 6000 --share-folder .  --download-folder . (troque a porta para cada cliente)
