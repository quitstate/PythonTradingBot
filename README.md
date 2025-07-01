# PythonTradingBot

Un sistema de trading algorítmico modular y extensible en Python, diseñado para operar en el mercado financiero utilizando MetaTrader 5. El bot incluye soporte para backtesting, análisis de sentimiento con modelos de IA, detector de anomalias con IA, gestión de riesgos, y notificaciones en tiempo real.

## 🚀 Características principales

- **Modularidad total**: Arquitectura desacoplada basada en componentes (estrategia, ejecución, riesgo, tamaño de posición, etc.).
- **Conexión directa con MetaTrader 5** para trading en vivo y backtesting.
- **Estrategias integradas**: Cruce de medias móviles, reversión a la media con RSI, entre otras.
- **Análisis de sentimiento** mediante modelos de _transformers_ y _PyTorch_.
- **Gestión del riesgo avanzada**: control por apalancamiento, tamaño de posición según porcentaje de riesgo o tamaño fijo.
- **Sistema de eventos y notificaciones** (incluye soporte para Telegram).
- **Utilidades gráficas y herramientas para investigación** (Jupyter Notebooks).

## 🧠 Arquitectura

```text
 trading_app.py
     └── trading_director/
         ├── data_source/
         ├── strategy_manager/
         ├── risk_manager/
         ├── position_sizer/
         ├── order_executor/
         ├── platform_connector/
         ├── portfolio/
         └── notifications/
               └── channels/
```

## 📂 Módulos destacados

- `strategy_manager/`: Gestión y ejecución de estrategias de trading.
- `risk_manager/`: Aplicación de reglas de gestión de riesgo.
- `position_sizer/`: Determinación del tamaño de la posición.
- `order_executor/`: Envío de órdenes a MetaTrader 5.
- `data_source/`: Obtención y preparación de datos de mercado.
- `sentiment_analyzer/`: Análisis de sentimiento con IA.
- `notifications/`: Envío de alertas mediante canales configurables.
- `backtesting/`: Soporte completo para pruebas históricas.
- `anomaly_detector/`: Detector de anomalias en datos con IA.

## 🛠️ Requisitos

Instala las dependencias desde el archivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

> Requiere tener MetaTrader 5 instalado en el sistema y la cuenta conectada.

## 📈 Backtesting

Incluye notebooks de Jupyter para validar estrategias y visualizar resultados:

- `backtesting.ipynb`
- `research_notebook.ipynb`

## 🔐 Variables de entorno

Utiliza un archivo `.env` con las siguientes claves:

```
TELEGRAM_TOKEN=tu_token
TELEGRAM_CHAT_ID=tu_chat_id
MT5_LOGIN=123456
MT5_PASSWORD=tu_password
MT5_SERVER=servidor_demo
```

## 📬 Notificaciones

Las alertas de operaciones y eventos clave pueden enviarse a través de Telegram u otros canales configurables.

## 📘 Licencia

Este proyecto se distribuye bajo la licencia MIT. Úsalo y modifícalo libremente para tus propios fines de investigación o desarrollo.
