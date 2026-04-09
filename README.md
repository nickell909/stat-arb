# Crypto Arbitrage Monitor — Система статистического арбитража криптовалют

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-39%20passed-green)]()

Приложение для мониторинга цен, анализа исторических данных криптовалютных бирж и поиска пар для статистического арбитража (парный трейдинг).

## 📖 Оглавление

- [Возможности](#возможности)
- [Архитектура системы](#архитектура-системы)
- [Установка](#установка)
- [Быстрый старт](#быстрый-старт)
- [Модуль 1: Сбор данных](#модуль-1-сбор-данных)
- [Модуль 2: Cointegration Engine](#модуль-2-cointegration-engine)
- [Модуль 3: Spread Calculator & Synthetic Builder](#модуль-3-spread-calculator--synthetic-builder)
- [API Reference](#api-reference)
- [Примеры использования](#примеры-использования)
- [Конфигурация](#конфигурация)
- [Запуск тестов](#запуск-тестов)
- [Структура проекта](#структура-проекта)

---

## Возможности

### 🔍 Поиск коинтегрированных пар
- Многоступенчатый скрининг (корреляция → ADF → Энгл-Грэнджер → Йохансен)
- Расчёт динамического hedge ratio через фильтр Калмана
- Оценка half-life возврата спреда к среднему

### 📊 Real-time мониторинг
- WebSocket подключение к Binance, Bybit, OKX
- Автоматический реконнект с exponential backoff
- Логирование latency и heartbeat-пинг

### 🧮 Синтетические инструменты
- Создание корзин из нескольких активов
- Оптимизация весов через PCA
- Нормализация к базовому значению 100

### 💾 Умное хранение данных
- SQLite база с OHLCV данными
- Загрузка только недостающих периодов
- Обработка выбросов и заполнение пропусков

---

## Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend UI (Planned)                       │
│  ┌─────────────┬──────────────┬────────────────┬─────────────┐  │
│  │Pair Scanner │Spread Monitor│Synthetic Builder│Dashboard   │  │
│  └─────────────┴──────────────┴────────────────┴─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ REST API / WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                      Backend Services                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Module 2: Cointegration Engine               │   │
│  │  ┌────────────┬─────────────┬────────────┬────────────┐  │   │
│  │  │ Screening  │Hedge Ratio  │ Half-Life  │ Johansen   │  │   │
│  │  │ (4 stages) │ OLS/Kalman  │ (OU process)│ Test 3+    │  │   │
│  │  └────────────┴─────────────┴────────────┴────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Module 3: Spread & Synthetic Builder              │   │
│  │  ┌────────────┬─────────────┬─────────────────────────┐  │   │
│  │  │ Z-Score    │ Percentile  │ Portfolio Constructor   │  │   │
│  │  │ Calculator │ Rank        │ (PCA, Equal, Custom)    │  │   │
│  │  └────────────┴─────────────┴─────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Module 1: Data Collection                    │   │
│  │  ┌────────────┬─────────────┬─────────────────────────┐  │   │
│  │  │ WebSocket  │ REST API    │ Normalizer &            │  │   │
│  │  │ Connectors │ Historical  │ Outlier Detection       │  │   │
│  │  │ (3 exchanges)│ Loader     │ Forward-Fill            │  │   │
│  │  └────────────┴─────────────┴─────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌──────────────┬──────────────┴──────────────┬───────────────┐
│   Binance    │           Bybit             │      OKX      │
│  WebSocket   │        REST API             │  WebSocket    │
│  REST API    │        WebSocket            │  REST API     │
└──────────────┴─────────────────────────────┴───────────────┘
```

---

## Установка

### Требования
- Python 3.12+
- pip 25.0+

### Шаг 1: Клонируйте репозиторий
```bash
git clone <repository-url>
cd crypto-arbitrage-monitor
```

### Шаг 2: Установите зависимости
```bash
pip install -r requirements.txt
```

**Основные зависимости:**
| Пакет | Версия | Назначение |
|-------|--------|------------|
| websockets | ≥12.0 | WebSocket подключения |
| pandas | ≥2.0.0 | Обработка временных рядов |
| numpy | ≥1.24.0 | Численные вычисления |
| sqlalchemy | ≥2.0.0 | Работа с БД |
| statsmodels | ≥0.14.0 | Статистические тесты (ADF, Johansen) |
| scipy | ≥1.11.0 | Научные вычисления |
| httpx | ≥0.25.0 | Асинхронные HTTP запросы |
| pytest | ≥7.4.0 | Тестирование |

---

## Быстрый старт

### Пример 1: Загрузка исторических данных
```python
import asyncio
from datetime import datetime, timedelta
from src.api.historical_data import HistoricalDataClient
from src.models.data_models import Timeframe

async def fetch_data():
    client = HistoricalDataClient()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    candles = await client.fetch_ohlcv(
        exchange='binance',
        symbol='BTC/USDT',
        timeframe=Timeframe.H1,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"Загружено {len(candles)} свечей")
    await client.close()

asyncio.run(fetch_data())
```

### Пример 2: Поиск коинтегрированных пар
```python
import pandas as pd
from src.cointegration.screening import CointegrationScreener
from src.cointegration.half_life import HalfLifeCalculator

# Загрузите данные в формате {symbol: pd.Series}
price_data = {
    'BTC/USDT': pd.Series(...),  # цены закрытия
    'ETH/USDT': pd.Series(...),
    'BNB/USDT': pd.Series(...),
}

# Скрининг пар
screener = CointegrationScreener(
    correlation_threshold=0.7,
    adf_pvalue_threshold=0.05,
    min_samples=60
)

pairs = screener.screen_pairs(price_data)

# Расчёт half-life
hl_calc = HalfLifeCalculator(min_half_life_days=2, max_half_life_days=60)

for pair in pairs:
    spread = price_data[pair.asset_1] - pair.hedge_ratio * price_data[pair.asset_2]
    half_life, details = hl_calc.calculate(spread, freq='1H')
    pair.half_life_days = half_life
    
    if details['is_tradable']:
        print(f"✅ {pair.asset_1}/{pair.asset_2}: "
              f"p-value={pair.p_value:.4f}, "
              f"hedge_ratio={pair.hedge_ratio:.4f}, "
              f"half-life={half_life:.1f} дней")
```

### Пример 3: Real-time подписка на тики
```python
import asyncio
from src.connectors.binance_connector import BinanceConnector
from src.models.data_models import TickData

async def on_tick(tick: TickData):
    print(f"{tick.symbol}: ${tick.last} (vol: {tick.volume})")

async def main():
    connector = BinanceConnector()
    connector.add_callback(on_tick)
    
    await connector.connect()
    await connector.subscribe(['BTC/USDT', 'ETH/USDT'])
    
    # Держим соединение 60 секунд
    await asyncio.sleep(60)
    await connector.disconnect()

asyncio.run(main())
```

---

## Модуль 1: Сбор данных

### 1.1 WebSocket коннекторы

Поддерживаемые биржи: **Binance**, **Bybit**, **OKX**

#### Базовый класс `BaseWebSocketConnector`

Все коннекторы наследуются от базового класса, который предоставляет:

| Функция | Описание |
|---------|----------|
| Автоматический реконнект | Exponential backoff (1s → 60s max) |
| Heartbeat ping | Каждые 30 секунд с таймаутом 10с |
| Логирование latency | Задержка пинга и сообщений |
| Message queue | Буфер на 10,000 сообщений |

#### Конфигурация подключения

```python
from src.connectors.base_connector import WebSocketConfig

config = WebSocketConfig(
    url="wss://stream.binance.com:9443/ws",
    ping_interval=30,           # секунды между пингами
    ping_timeout=10,            # таймаут ожидания понга
    reconnect_delay_base=1.0,   # начальная задержка реконнекта
    reconnect_delay_max=60.0,   # максимальная задержка
    message_queue_size=10000    # размер буфера
)
```

#### Реализованные коннекторы

| Класс | Биржа | Документация |
|-------|-------|--------------|
| `BinanceConnector` | Binance | [Binance API](https://binance-docs.github.io/apidocs/) |
| `BybitConnector` | Bybit | [Bybit API](https://bybit-exchange.github.io/docs/) |
| `OKXConnector` | OKX | [OKX API](https://www.okx.com/docs-v5/en/) |

#### Нормализация символов

Все коннекторы приводят символы к единому формату **BASE/QUOTE**:

| Биржа | Исходный формат | Нормализованный |
|-------|-----------------|-----------------|
| Binance | `BTCUSDT` | `BTC/USDT` |
| Bybit | `BTCUSDT` | `BTC/USDT` |
| OKX | `BTC-USDT` | `BTC/USDT` |

### 1.2 REST API — исторические данные

Класс `HistoricalDataClient` для загрузки OHLCV свечей.

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|----------|
| `exchange` | str | Биржа: `binance`, `bybit`, `okx` |
| `symbol` | str | Символ в формате `BASE/QUOTE` |
| `timeframe` | Timeframe | Таймфрейм: `M1`, `M5`, `M15`, `H1`, `H4`, `D1` |
| `start_date` | datetime | Дата начала периода |
| `end_date` | datetime | Дата конца периода |
| `limit` | int | Макс. свечей за запрос (по умолчанию 1000) |

#### Умная загрузка

Метод `get_missing_periods()` определяет отсутствующие периоды в БД и догружает только их.

#### Параллельная загрузка

```python
requests = [
    ('binance', 'BTC/USDT', Timeframe.H1, start, end),
    ('binance', 'ETH/USDT', Timeframe.H1, start, end),
    ('bybit', 'BTC/USDT', Timeframe.H1, start, end),
]

results = await client.fetch_parallel(requests)
# results = {'binance:BTC/USDT:1h': [...], ...}
```

#### Rate limits

| Биржа | Requests/sec | Requests/min |
|-------|--------------|--------------|
| Binance | 10 | 1200 |
| Bybit | 10 | 600 |
| OKX | 5 | 300 |

### 1.3 Нормализация данных

Класс `DataNormalizer` обрабатывает входящие данные.

#### Обработка выбросов

```python
normalizer = DataNormalizer(outlier_threshold_pct=5.0)

# Обнаружение выбросов
outliers = normalizer.detect_outliers(prices=[100, 101, 102, 200, 103])
#返回: [(3, 200, 102)]  # индекс, цена, предыдущая

# Удаление выбросов из OHLCV
cleaned = normalizer.remove_outliers(candles, replace_with_previous=True)
```

#### Заполнение пропусков

Forward-fill заполняет пропущенные свечи последними известными значениями:

```python
filled = normalizer.fill_gaps(candles, timeframe_minutes=60)
# Пропущенные свечи помечаются is_interpolated=True
```

#### Единая схема данных

```python
@dataclass
class OHLCV:
    exchange: str          # Название биржи
    symbol: str            # BASE/QUOTE
    timestamp_ms: int      # Unix timestamp в мс
    open: float            # Цена открытия
    high: float            # Максимум
    low: float             # Минимум
    close: float           # Цена закрытия
    volume: float          # Объём в базовой валюте
    quote_volume: float    # Объём в котируемой валюте
    is_interpolated: bool  # Флаг искусственной свечи
```

---

## Модуль 2: Cointegration Engine

Ядро системы для поиска статистически связанных пар активов.

### 2.1 Скрининг пар

Четырёхэтапный процесс фильтрации:

#### Этап 1: Предфильтрация по корреляции
Отсеивает пары с корреляцией Пирсона ниже порога (по умолчанию 0.7).

```python
screener = CointegrationScreener(correlation_threshold=0.7)
correlated_pairs = screener._filter_by_correlation(price_data, symbols)
```

#### Этап 2: Тест на единичный корень (ADF)
Проверяет, что оба ряда нестационарны (I(1)).

```python
from statsmodels.tsa.stattools import adfuller

adf_result = adfuller(prices, maxlag=1, regression='c', autolag='AIC')
is_stationary = adf_result[1] < 0.05  # p-value
```

#### Этап 3: Тест Энгла-Грэнджера
Для отфильтрованных пар строится OLS-регрессия, затем ADF тест применяется к остаткам.

```python
from statsmodels.tsa.stattools import coint

score, p_value, _ = coint(prices_1, prices_2, trend='c', method='aeg')
if p_value < 0.05:
    print("Пара коинтегрирована!")
```

#### Этап 4: Тест Йохансена
Для групп из 3+ активов используется векторный тест Йохансена.

```python
from src.cointegration.johansen import JohansenTest

johansen = JohansenTest(confidence_level=0.95)
result = johansen.test(price_matrix)  # матрица цен [n_samples, n_assets]

print(f"Количество коинтегрирующих векторов: {result.num_cointegrating_vectors}")
print(f"Веса портфеля: {result.cointegrating_vectors[0]}")
```

### 2.2 Расчёт Hedge Ratio

Два метода на выбор:

#### OLS (статический)
Простая линейная регрессия: `price_1 = α + β * price_2 + ε`

```python
calculator = HedgeRatioCalculator(method='ols')
hedge_ratio, _ = calculator.calculate(prices_1, prices_2)
# hedge_ratio = β из регрессии
```

#### Kalman Filter (динамический)
Моделирует hedge ratio как скрытую переменную, изменяющуюся во времени.

```python
calculator = HedgeRatioCalculator(method='kalman')
hedge_ratio, time_series = calculator.calculate(prices_1, prices_2)

# time_series содержит:
# - timestamps: список дат
# - hedge_ratios: эволюция β во времени
# - std_errors: стандартные ошибки
```

**Сравнение методов:**

| Характеристика | OLS | Kalman Filter |
|----------------|-----|---------------|
| Адаптивность | Нет | Да |
| Вычислительная сложность | Низкая | Средняя |
| Подходит для | Стабильных рынков | Волатильных рынков |
| Интерпретируемость | Высокая | Средняя |

#### Rolling OLS
Компромиссный вариант — скользящее окно OLS:

```python
rolling_hr = calculator.rolling_ols_hedge_ratio(prices_1, prices_2, window=60)
# Возвращает pd.Series с hedge ratio для каждого окна
```

### 2.3 Half-life расчёт

Оценка времени возврата спреда к среднему через процесс Орнштейна-Уленбека:

`dS = κ(μ - S)dt + σdW`

**Half-life = ln(2) / κ**

```python
from src.cointegration.half_life import HalfLifeCalculator

hl_calc = HalfLifeCalculator(
    min_half_life_days=2.0,   # минимальный tradable half-life
    max_half_life_days=60.0   # максимальный tradable half-life
)

spread = prices_1 - hedge_ratio * prices_2
half_life, details = hl_calc.calculate(spread, freq='1H')

print(f"Half-life: {half_life:.2f} дней")
print(f"Tradable: {details['is_tradable']}")
print(f"Mean reversion rate (κ): {details['kappa']:.6f}")
```

**Интерпретация half-life:**

| Диапазон | Значение |
|----------|----------|
| < 2 дней | Слишком быстро, высокий шум |
| 2–60 дней | **Оптимально для торговли** |
| > 60 дней | Слишком медленно, капитал связывается |
| ∞ | Нет mean reversion (не торгуемо) |

### Модели данных

#### CointegrationPair

```python
@dataclass
class CointegrationPair:
    pair_id: str                # Уникальный ID пары
    asset_1: str                # Первый актив
    asset_2: str                # Второй актив
    hedge_ratio: float          # Коэффициент хеджирования
    p_value: float              # p-value теста Энгла-Грэнджера
    coint_score: float          # Статистика теста
    half_life_days: float       # Half-life в днях
    last_checked_at: datetime   # Время последнего анализа
    correlation: float          # Корреляция Пирсона
    method: str                 # 'ols' или 'kalman'
```

---

## Модуль 3: Spread Calculator & Synthetic Builder

### 3.1 Расчёт спреда

Для каждой пары рассчитываются метрики в реальном времени:

#### Raw Spread
`S = price_1 - hedge_ratio * price_2`

#### Z-Score
`Z = (S - rolling_mean(S, window)) / rolling_std(S, window)`

```python
def calculate_z_score(spread: pd.Series, window: int = 20) -> pd.Series:
    rolling_mean = spread.rolling(window=window).mean()
    rolling_std = spread.rolling(window=window).std()
    return (spread - rolling_mean) / rolling_std
```

#### Percentile Rank
Позиция текущего спреда в распределении за последние N дней:

```python
from scipy.stats import percentileofscore

percentile = percentileofscore(historical_spread, current_spread) / 100
# 0.95 означает, что спред выше 95% исторических значений
```

#### Полосы отклонения

| Полоса | Значение | Сигнал |
|--------|----------|--------|
| ±1σ | 68% доверительный интервал | Наблюдение |
| ±2σ | 95% доверительный интервал | **Вход в позицию** |
| ±3σ | 99.7% доверительный интервал | Сильный сигнал |

### 3.2 Синтетические инструменты

Конструктор позволяет создавать корзины из нескольких активов.

#### Типы синтетиков

##### 1. Равновзвешенный
Все активы с одинаковым весом:

```python
weights = {'BTC/USDT': 0.33, 'ETH/USDT': 0.33, 'BNB/USDT': 0.34}
```

##### 2. По объёму торгов
Вес пропорционален объёму:

```python
volumes = {'BTC/USDT': 1000, 'ETH/USDT': 500, 'BNB/USDT': 200}
total = sum(volumes.values())
weights = {k: v/total for k, v in volumes.items()}
```

##### 3. PCA-портфель
Автоматический расчёт весов через первую главную компоненту:

```python
from sklearn.decomposition import PCA
import numpy as np

# price_matrix: [n_samples, n_assets]
pca = PCA(n_components=1)
pca.fit(price_matrix)
weights = pca.components_[0]
weights = weights / np.sum(np.abs(weights))  # нормализация
```

##### 4. Пользовательский
Произвольные веса, введённые вручную.

#### Нормализация к базовому значению

Синтетик нормализуется к 100 на дату старта:

```python
def normalize_portfolio(portfolio_values: pd.Series, base_date: datetime) -> pd.Series:
    base_value = portfolio_values.loc[base_date]
    return (portfolio_values / base_value) * 100
```

#### Мониторинг синтетика

После создания синтетик ведёт себя как обычный инструмент:
- Можно строить пары с другими активами
- Рассчитывать спреды и z-score
- Отслеживать сигналы

---

## API Reference

### Connectors

#### `BaseWebSocketConnector`

| Метод | Описание |
|-------|----------|
| `connect()` | Подключение к WebSocket |
| `disconnect()` | Отключение |
| `subscribe(symbols: List[str])` | Подписка на символы |
| `unsubscribe(symbols: List[str])` | Отписка |
| `add_callback(callback)` | Добавление обработчика тиков |
| `stats` | Статистика подключения (property) |

#### `HistoricalDataClient`

| Метод | Описание |
|-------|----------|
| `fetch_ohlcv(exchange, symbol, timeframe, start, end)` | Загрузка свечей |
| `fetch_parallel(requests)` | Параллельная загрузка |
| `close()` | Закрытие HTTP клиента |

### Cointegration

#### `CointegrationScreener`

| Метод | Описание |
|-------|----------|
| `screen_pairs(price_data, start_date, end_date)` | Полный скрининг |
| `_filter_by_correlation(price_data, symbols)` | Фильтр по корреляции |
| `get_correlation_matrix(price_data)` | Матрица корреляций |

#### `HedgeRatioCalculator`

| Метод | Описание |
|-------|----------|
| `calculate(prices_1, prices_2, method)` | Расчёт hedge ratio |
| `calculate_spread(prices_1, prices_2, hedge_ratio)` | Расчёт спреда |
| `rolling_ols_hedge_ratio(prices_1, prices_2, window)` | Скользящий OLS |

#### `HalfLifeCalculator`

| Метод | Описание |
|-------|----------|
| `calculate(spread, freq)` | Расчёт half-life |
| `is_tradable(half_life_days)` | Проверка диапазона |
| `get_optimal_pairs(results)` | Фильтрация оптимальных пар |

#### `JohansenTest`

| Метод | Описание |
|-------|----------|
| `test(price_matrix)` | Тест Йохансена |
| `get_portfolio_weights(result)` | Веса портфеля |
| `create_portfolio_series(price_matrix, weights)` | Серия портфеля |

### Data

#### `DataNormalizer`

| Метод | Описание |
|-------|----------|
| `detect_outliers(prices)` | Обнаружение выбросов |
| `remove_outliers(candles)` | Удаление выбросов |
| `fill_gaps(candles, timeframe_minutes)` | Заполнение пропусков |
| `candles_to_dataframe(candles)` | Конвертация в DataFrame |
| `validate_candle(candle)` | Валидация свечи |

#### `DatabaseManager`

| Метод | Описание |
|-------|----------|
| `save_candles(candles, timeframe)` | Сохранение свечей |
| `get_candles(exchange, symbol, timeframe, start, end)` | Загрузка свечей |
| `get_missing_periods(exchange, symbol, timeframe, start, end)` | Поиск пропусков |
| `get_latest_timestamp(exchange, symbol, timeframe)` | Последняя дата в БД |

---

## Примеры использования

### Полный рабочий пайплайн

```python
import asyncio
from datetime import datetime, timedelta
from src.api.historical_data import HistoricalDataClient
from src.data.database import DatabaseManager
from src.data.normalizer import DataNormalizer
from src.cointegration.screening import CointegrationScreener
from src.cointegration.half_life import HalfLifeCalculator
from src.models.data_models import Timeframe

async def run_full_pipeline():
    # 1. Инициализация
    api_client = HistoricalDataClient()
    db = DatabaseManager("crypto_data.db")
    normalizer = DataNormalizer(outlier_threshold_pct=5.0)
    screener = CointegrationScreener(correlation_threshold=0.7)
    hl_calc = HalfLifeCalculator()
    
    # 2. Загрузка данных
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
    
    price_data = {}
    for symbol in symbols:
        # Проверка БД на наличие данных
        missing = await db.get_missing_periods(
            'binance', symbol, Timeframe.D1, start_date, end_date
        )
        
        if missing:
            candles = await api_client.fetch_ohlcv(
                'binance', symbol, Timeframe.D1, start_date, end_date
            )
            
            # Нормализация
            candles = normalizer.filter_invalid_candles(candles)
            candles = normalizer.remove_outliers(candles)
            
            # Сохранение
            await db.save_candles(candles, Timeframe.D1)
        else:
            candles = await db.get_candles(
                'binance', symbol, Timeframe.D1, start_date, end_date
            )
        
        # Конвертация в Series
        df = normalizer.candles_to_dataframe(candles)
        price_data[symbol] = df['close']
    
    # 3. Скрининг пар
    pairs = screener.screen_pairs(price_data)
    print(f"Найдено {len(pairs)} потенциальных пар")
    
    # 4. Расчёт half-life и фильтрация
    tradable_pairs = []
    for pair in pairs:
        spread = price_data[pair.asset_1] - pair.hedge_ratio * price_data[pair.asset_2]
        half_life, details = hl_calc.calculate(spread, freq='1D')
        pair.half_life_days = half_life
        
        if details['is_tradable']:
            tradable_pairs.append(pair)
            print(f"✅ {pair.asset_1}/{pair.asset_2}: "
                  f"p={pair.p_value:.4f}, HR={pair.hedge_ratio:.3f}, "
                  f"HL={half_life:.1f}d")
    
    await api_client.close()
    return tradable_pairs

# Запуск
pairs = asyncio.run(run_full_pipeline())
```

### Real-time мониторинг спреда

```python
import asyncio
from src.connectors.binance_connector import BinanceConnector
from src.cointegration.hedge_ratio import HedgeRatioCalculator

class SpreadMonitor:
    def __init__(self, asset1, asset2, hedge_ratio):
        self.asset1 = asset1
        self.asset2 = asset2
        self.hedge_ratio = hedge_ratio
        self.prices1 = []
        self.prices2 = []
        self.spread_history = []
    
    async def on_tick(self, tick):
        if tick.symbol == self.asset1:
            self.prices1.append(tick.last)
        elif tick.symbol == self.asset2:
            self.prices2.append(tick.last)
        
        if len(self.prices1) > 20 and len(self.prices2) > 20:
            # Расчёт спреда
            spread = self.prices1[-1] - self.hedge_ratio * self.prices2[-1]
            self.spread_history.append(spread)
            
            # Z-score
            mean = sum(self.spread_history[-20:]) / 20
            std = (sum((x - mean)**2 for x in self.spread_history[-20:]) / 20) ** 0.5
            
            if std > 0:
                z_score = (spread - mean) / std
                
                # Сигналы
                if abs(z_score) > 2.0:
                    direction = "SHORT" if z_score > 0 else "LONG"
                    print(f"🚨 SIGNAL: {direction} spread on {self.asset1}/{self.asset2}")
                    print(f"   Z-score: {z_score:.2f}, Spread: {spread:.2f}")

async def main():
    monitor = SpreadMonitor('BTC/USDT', 'ETH/USDT', hedge_ratio=0.065)
    
    connector = BinanceConnector()
    connector.add_callback(monitor.on_tick)
    
    await connector.connect()
    await connector.subscribe(['BTC/USDT', 'ETH/USDT'])
    
    # Мониторинг 24 часа
    await asyncio.sleep(24 * 60 * 60)
    await connector.disconnect()

asyncio.run(main())
```

---

## Конфигурация

### Переменные окружения

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `DB_PATH` | `crypto_data.db` | Путь к SQLite базе |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
| `BINANCE_WS_URL` | `wss://stream.binance.com:9443/ws` | WebSocket Binance |
| `BYBIT_WS_URL` | `wss://stream.bybit.com/v5/public/spot` | WebSocket Bybit |
| `OKX_WS_URL` | `wss://ws.okx.com:8443/ws/v5/public` | WebSocket OKX |

### Параметры скрининга (рекомендуемые)

```yaml
screening:
  correlation_threshold: 0.7      # Мин. корреляция Пирсона
  adf_pvalue_threshold: 0.05      # Макс. p-value для ADF
  min_samples: 60                 # Мин. количество точек
  
half_life:
  min_days: 2.0                   # Мин. half-life для торговли
  max_days: 60.0                  # Макс. half-life для торговли
  
trading:
  entry_z_score: 2.0              # Вход при |Z| > 2
  exit_z_score: 0.5               # Выход при |Z| < 0.5
  stop_loss_z_score: 3.5          # Стоп-лосс при |Z| > 3.5
  rolling_window: 20              # Окно для расчёта Z-score
```

---

## Запуск тестов

```bash
# Установка зависимостей для тестирования
pip install pytest pytest-asyncio

# Запуск всех тестов
pytest tests/ -v

# Запуск с покрытием
pytest tests/ -v --cov=src

# Запуск конкретного модуля
pytest tests/test_cointegration.py -v
```

### Статус тестов

| Модуль | Тестов | Статус |
|--------|--------|--------|
| test_cointegration.py | 23 | ✅ Passed |
| test_connectors.py | 8 | ✅ Passed |
| test_data.py | 8 | ✅ Passed |
| **Итого** | **39** | **✅ 100%** |

---

## Структура проекта

```
crypto-arbitrage-monitor/
├── src/
│   ├── __init__.py
│   ├── main.py                     # Точка входа
│   │
│   ├── connectors/                 # WebSocket коннекторы
│   │   ├── __init__.py
│   │   ├── base_connector.py       # Базовый класс
│   │   ├── binance_connector.py    # Binance адаптер
│   │   ├── bybit_connector.py      # Bybit адаптер
│   │   ├── okx_connector.py        # OKX адаптер
│   │   └── exchange_manager.py     # Менеджер подключений
│   │
│   ├── api/                        # REST API клиенты
│   │   ├── __init__.py
│   │   └── historical_data.py      # Загрузка OHLCV
│   │
│   ├── data/                       # Обработка данных
│   │   ├── __init__.py
│   │   ├── database.py             # SQLite менеджер
│   │   └── normalizer.py           # Нормализация
│   │
│   ├── cointegration/              # Ядро анализа
│   │   ├── __init__.py
│   │   ├── models.py               # Модели данных
│   │   ├── screening.py            # Скрининг пар
│   │   ├── hedge_ratio.py          # Расчёт коэффициентов
│   │   ├── half_life.py           # Half-life калькулятор
│   │   └── johansen.py             # Тест Йохансена
│   │
│   ├── models/                     # Общие модели
│   │   ├── __init__.py
│   │   └── data_models.py          # TickData, OHLCV, Spread
│   │
│   ├── services/                   # Бизнес-логика
│   │   └── (reserved)
│   │
│   └── utils/                      # Утилиты
│       └── (reserved)
│
├── tests/
│   ├── test_cointegration.py       # Тесты ядра
│   ├── test_connectors.py          # Тесты коннекторов
│   └── test_data.py                # Тесты данных
│
├── config/                         # Конфигурация
├── examples/                       # Примеры использования
│   └── cointegration_example.py
│
├── requirements.txt                # Зависимости
└── README.md                       # Документация
```

---

## Лицензия

MIT License — см. файл [LICENSE](LICENSE) для деталей.

## Contributing

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## Контакты

- Issues: GitHub Issues
- Email: support@example.com

---

*Документация актуальна на версию 1.0.0*
