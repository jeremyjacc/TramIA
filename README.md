# TramIA

MVP de un sistema multiagente para orientar tramites y servicios publicos con trazabilidad y supervision humana.

## Que resuelve

1. Recibe la solicitud ciudadana y sus documentos declarados.
2. Clasifica el tramite con un agente especializado.
3. Consulta un catalogo referencial de requisitos y enlaces oficiales.
4. Valida que se hayan presentado los documentos requeridos.
5. Genera una guia personalizada y conserva cada accion en una bitacora SQLite.
6. Deriva automaticamente a un funcionario los casos que no puede identificar con seguridad.

> Los requisitos y costos incluidos son solo demostrativos. Antes de usar TramIA con ciudadanos, el catalogo debe alimentarse y validarse con las fuentes oficiales vigentes de cada institucion.

## Arquitectura

```text
Solicitud ciudadana
       |
Agente de clasificacion
       |
Agente de informacion oficial --> Catalogo referencial
       |
Agente de validacion documental
       |
Agente de guia personalizada --> Guia + estado
       |
  SQLite: solicitudes, documentos y trazabilidad
       |
Funcionario (solo casos derivados)
```

## Ejecutar

No requiere dependencias externas: se usa Python 3.10 o superior y la biblioteca estandar.

```powershell
cd TramIA
python -m app.server
```

El servicio se inicia en `http://127.0.0.1:8000`. La base de datos local se crea como `tramia.db` y no debe subirse al repositorio.

## Crear una solicitud

```powershell
$body = @{
  citizen_name = "Ana Perez"
  email = "ana@example.com"
  description = "Necesito renovar mi cedula vencida"
  documents = @(
    @{ name = "Cedula de identidad"; valid = $true }
    @{ name = "Comprobante de pago"; valid = $true }
  )
} | ConvertTo-Json -Depth 4

Invoke-RestMethod http://127.0.0.1:8000/api/solicitudes `
  -Method Post -ContentType "application/json" -Body $body
```

## Endpoints

| Metodo | Ruta | Funcion |
|---|---|---|
| `POST` | `/api/solicitudes` | Crea, clasifica y orienta una solicitud. |
| `GET` | `/api/solicitudes/{id}` | Devuelve solicitud, guia, documentos y trazabilidad. |
| `POST` | `/api/solicitudes/{id}/escalar` | Solicita revision humana manual. |
| `GET` | `/api/funcionarios/pendientes` | Lista solicitudes derivadas a un funcionario. |

El cuerpo de escalamiento es `{"reason": "Descripcion del motivo"}`.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas cubren la orientacion automatica, la derivacion de un tramite desconocido y el escalamiento manual.

## Siguientes pasos recomendados

- Reemplazar el catalogo demostrativo por integraciones con fuentes oficiales autorizadas.
- Incorporar autenticacion y roles para ciudadanos y funcionarios.
- Almacenar archivos de documentos de forma segura; este MVP solo maneja sus metadatos.
- Agregar una interfaz web y mecanismos de privacidad, consentimiento y retencion de datos.
