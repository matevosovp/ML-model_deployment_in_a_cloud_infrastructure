# Security policy

## Supported version

Security fixes применяются к последней версии ветки `main`.

## Reporting

Не публикуйте потенциальную уязвимость, секрет или способ эксплуатации в обычном issue. Используйте private vulnerability reporting во вкладке **Security** репозитория. Если функция недоступна, сначала свяжитесь с владельцем профиля через GitHub, не раскрывая технические детали публично.

## Scope notes

- сервис намеренно не поддерживает исполняемые `.pkl`/`.joblib`; native `.cbm` принимается только с checksum из manifest;
- локальный Compose bind-ит порты к `127.0.0.1` и не предназначен для публичного интернета;
- для внешнего deployment обязательны TLS, authentication, rate limiting, secret manager и network policy.
