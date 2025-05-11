# 🚀 Deploy do PhotoCloud com Docker

## 🐳 Como Rodar Localmente com Docker

1. **Clone o projeto ou descompacte**
2. **Execute os comandos abaixo no terminal**:

```bash
docker-compose up --build
```

3. **Acesse em seu navegador:**
```
http://localhost:8000
```

## 📦 Estrutura Montada
- Uploads persistem no volume: `./static/uploads`
- Comentários e usuários também são salvos localmente

## 🌐 Para Deploy Externo (ex: Render ou VPS)
- Suba o Dockerfile + requirements.txt + app com git ou scp
- Execute: `docker-compose up --build -d`

---

**Admin padrão:** Crie com usuário `admin`, ele terá acesso ao painel `/admin`.