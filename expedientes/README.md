# expedientes/

Un directorio por expediente, con la referencia interna ATRIO (`ATYYxx`) como nombre. Se crean con `scripts/nuevo_expediente.py`.

```
expedientes/AT2607/
├── entrada/        documentación recibida
├── salida/         entregables generados
├── FICHA.md        ficha del expediente
└── CRONOLOGIA.md   cronología de actos y escritos
```

**Confidencialidad (CLAUDE.md apartado 10):** los datos de clientes no salen de esta carpeta. Por defecto `.gitignore` excluye del control de versiones todos los expedientes salvo `_EJEMPLO/` (caso anonimizado). Si se quiere versionar un expediente concreto, hay que añadir una excepción explícita en `.gitignore`.
