# Model card: Sprint2 CatBoost real-estate regressor

## Назначение

Учебная регрессионная модель демонстрирует deployment lifecycle для оценки стоимости объекта недвижимости. Она предназначена для portfolio/demo inference, а не для реальных финансовых решений.

## Artifact

| Поле | Значение |
|---|---|
| Framework | CatBoost `CatBoostRegressor` |
| Serialization | native CatBoost `.cbm` |
| Version | `sprint2-catboost-2025-12-27` |
| Feature contract | `engineered-real-estate-v1` |
| Features | 29 ordered numeric values |
| Output | стоимость объекта, `float` |
| SHA-256 | `b623ad39f6a19b1aedcc508ae3cd31b74928e9f99a9eaea1765e33c720b750da` |

Manifest проверяется до десериализации. При несовпадении checksum или feature order сервис не становится ready.

## Входные данные

Модель ожидает числовые признаки недвижимости и заранее рассчитанные взаимодействия признаков. Полный порядок определён `PropertyFeatures` в `services/ml_service/schemas.py` и сверяется с `feature_names_` CatBoost.

Этот контракт является legacy-ограничением: preprocessing должен выполняться тем же проверенным pipeline, который использовался при обучении. Для следующей версии рекомендуется сериализовать preprocessing вместе с estimator и принимать только raw domain fields.

## Ограничения и риски

- неизвестны репрезентативность и временной период training sample;
- модель может плохо переноситься на другой город, сегмент рынка или период;
- engineered values от клиента могут быть внутренне несогласованными;
- prediction не является рыночной оценкой, офертой или финансовой рекомендацией;
- online drift, calibration и качество после deployment не измеряются;
- checksum должен обновляться только вместе с review новой версии native artifact.

## Проверка deployment

CI загружает bundled artifact на закреплённом Python runtime, проверяет manifest, выполняет реальное предсказание, затем повторяет запрос через собранный Docker-контейнер. Эти проверки подтверждают техническую совместимость, но не ML-качество.
