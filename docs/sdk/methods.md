# Справочник методов

Сгенерировано из кода: `python scripts/generate_method_reference.py`. Всего **167** методов.

Каждый метод вызывается на клиенте: `await client.<метод>(...)`.

## Интернет-эквайринг (pay-gateway)

### `acquiring_authentication`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `complete_payment` | POST | `/{api_version}/sites/{site_uid}/payments/{payment_uid}/complete` | После успешного прохождения дополнительной аутентификации, ТСП необходимо отправить запрос |

### `acquiring_bank_form`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `cancel_invoice` | POST | `/{api_version}/sites/{site_uid}/invoices/{invoice_uid}/cancel` | Отменить ранее созданный счёт |
| `create_invoice` | POST | `/invoice/v1.0/bills` | Метод для создания счёта на оплату |
| `get_invoice` | GET | `/invoice/v1.0/bills/{customer_code}/{document_id}/file` | Метод для получения файла выставленного счёта |

### `acquiring_cashbox_links`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `activate_cash_register_qr_code` | POST | `/{api_version}/sites/{site_uid}/sbp/qrc/cash-register-qrc/{qrc_id}/activations` | Активировать Кассовую ссылку СБП |
| `create_cash_register_qr_code` | POST | `/{api_version}/sites/{site_uid}/sbp/qrc/cash-register-qrc` | Создать Кассовую ссылку СБП |
| `deactivate_cash_register_qr_code` | DELETE | `/{api_version}/sites/{site_uid}/sbp/qrc/cash-register-qrc/{qrc_id}/activations/current` | Деактивировать Кассовую ссылку СБП |
| `get_cash_register_qr_code_status` | GET | `/{api_version}/sites/{site_uid}/sbp/qrc/cash-register-qrc/{qrc_id}/status` | Получить статус Кассовой ссылки СБП |
| `get_payment_by_cash_register_qrc_activation_uid` | GET | `/{api_version}/sites/{site_uid}/sbp/qrc/cash-register-qrc/{qrc_id}/activations/{activation_uid}/payment` | Получить платёж по активации Кассовой ссылки СБП |

### `acquiring_confirmation`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_capture` | POST | `/{api_version}/sites/{site_uid}/payments/{payment_uid}/captures` | Подтвердить платёж после холдирования средств. Данный запрос необходим для подтверждения о |
| `get_capture` | GET | `/{api_version}/sites/{site_uid}/payments/{payment_uid}/captures/{capture_uid}` | Получить статус указанного подтверждения платежа |
| `get_captures` | GET | `/{api_version}/sites/{site_uid}/payments/{payment_uid}/captures` | Получить список попыток подтверждения платежа |

### `acquiring_functional_links`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_qr_code` | POST | `/{api_version}/sites/{site_uid}/sbp/qrc` | Создать Функциональную ссылку СБП |
| `get_payments_by_qrc_id` | GET | `/{api_version}/sites/{site_uid}/sbp/qrc/{qrc_id}/payments` | Получить платежи по ранее зарегистрированной Функциональной ссылке СБП |
| `get_qr_code` | GET | `/sbp/v1.0/qr-code/{qrc_id}` | Метод для получения информации о QR-коде |
| `get_tokenization_result` | GET | `/{api_version}/sites/{site_uid}/sbp/qrc/{qrc_id}/tokenization/result` | Получить результат выполнения привязки счёта по ранее зарегистрированной Функциональной сс |

### `acquiring_merchant_form`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_payment` | POST | `/{api_version}/sites/{site_uid}/payments` | Создать платёжную транзакцию |
| `get_payment` | GET | `/{api_version}/sites/{site_uid}/payments/{payment_uid}` | Получить информацию о платёжной транзакции |

### `acquiring_payment_tokens`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `handle_card_token_operation` | POST | `/{api_version}/sites/{site_uid}/card-token-operations` | Выполняет операции с платёжным токеном карты |

### `acquiring_refunds`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_refund` | POST | `/{api_version}/sites/{site_uid}/payments/{payment_uid}/refunds` | Запрос предназначен для возврата средств по платежу |
| `get_refund` | GET | `/{api_version}/sites/{site_uid}/payments/{payment_uid}/refunds/{refund_uid}` | Получить статус указанного возврата |
| `get_refunds` | GET | `/{api_version}/sites/{site_uid}/payments/{payment_uid}/refunds` | Получить статусы всех возвратов для данного платежа |

### `acquiring_webhooks`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `capture_notification` | POST | `/merchant-notifications-url/capture` | Уведомление об изменении статуса подтверждения |
| `payment_notification` | POST | `/merchant-notifications-url/payment` | Уведомление об изменении статуса платежа |
| `refund_notification` | POST | `/merchant-notifications-url/refund` | Уведомление об изменении статуса возврата |
| `tokenization_decision_notification` | POST | `/merchant-notifications-url/tokenization-decision` | Уведомление о результате выполнения привязки счёта |

## Маркетплейс-выплаты (medusa)

### `marketplace_orders`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_order` | POST | `/medusa/v1.0/orders` | Создать заказ |
| `create_order_v2` | POST | `/medusa/v2.0/orders` | Создать заказ v2 |
| `create_order_v3` | POST | `/medusa/v3.0/orders` | Создать заказ v3 |
| `get_order` | GET | `/medusa/v1.0/orders/{order_ext_id}` | Получить заказ |
| `get_order_list` | GET | `/medusa/v1.0/orders` | Получить список заказов |
| `get_order_report` | GET | `/medusa/v1.0/orders/report` | Получить отчет по заказам |
| `get_order_v2` | GET | `/medusa/v2.0/orders/{order_ext_id}` | Получить заказ v2 |
| `get_order_v3` | GET | `/medusa/v3.0/orders/{order_ext_id}` | Получить заказ v3 |
| `make_order_services_decision` | POST | `/medusa/v1.0/orders/{order_ext_id}/decisions` | Подтвердить оказание услуги |
| `update_order` | PATCH | `/medusa/v1.0/orders/{order_ext_id}` | Изменить услуги в заказе |

### `marketplace_recipients`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `add_card_recipient_payout_method` | POST | `/medusa/v1.0/recipients/{recipient_ext_id}/payout_methods/cards` | Добавить карту |
| `add_sbp_recipient_payout_method` | POST | `/medusa/v1.0/recipients/{recipient_ext_id}/payout_methods/sbp` | Добавить метод выплаты СБП |
| `create_recipient` | POST | `/medusa/v1.0/recipients` | Создать получателя |
| `delete_card_recipient_payout_method` | DELETE | `/medusa/v1.0/recipients/{recipient_ext_id}/payout_methods/cards/{payout_method_ext_id}` | Удалить карту |
| `delete_recipient_payout_method` | DELETE | `/medusa/v1.0/recipients/{recipient_ext_id}/payout_methods/{payout_method_ext_id}` | Удалить метод выплаты |
| `get_recipient` | GET | `/medusa/v1.0/recipients/{recipient_ext_id}` | Детали о получателе |
| `get_recipient_v2` | GET | `/medusa/v2.0/recipients/{recipient_ext_id}` | Детали о получателе v2 |
| `list_recipient_sbp_banks` | GET | `/medusa/v1.0/recipients/sbp-banks/` | Получить список банков-получателей СБП |
| `update_recipient` | PATCH | `/medusa/v1.0/recipients/{recipient_ext_id}` | Обновить получателя |

## Номинальные счета (cyclops)

### `beneficiaries`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `activate_beneficiary_v2` | POST | `/v2/jsonrpc/activate_beneficiary` | Метод активации бенефициара |
| `add_beneficiary_documents_data_v3` | POST | `/v3/jsonrpc/add_beneficiary_documents_data` | Создает записи с данными документов |
| `create_beneficiary_fl_v2` | POST | `/v2/jsonrpc/create_beneficiary_fl` | Метод для создания бенефициара, если он является физическим лицом |
| `create_beneficiary_ip_v2` | POST | `/v2/jsonrpc/create_beneficiary_ip` | Метод для создания бенефициара, если он является индивидуальным предпринимателем |
| `create_beneficiary_ul_v2` | POST | `/v2/jsonrpc/create_beneficiary_ul` | Метод для создания бенефициара, если он является юридическим лицом |
| `create_beneficiary_v3` | POST | `/v3/jsonrpc/create_beneficiary` | Метод для создания бенефициара, если он является ИП, самозанятым или физлицом |
| `deactivate_beneficiary_v2` | POST | `/v2/jsonrpc/deactivate_beneficiary` | Метод деактивации бенефициара |
| `get_beneficiary_documents_data_v3` | POST | `/v3/jsonrpc/get_beneficiary_documents_data` | Возвращает данные о последних загруженных дукументах, а так же, о валидных в данный момент |
| `get_beneficiary_restrictions_v2` | POST | `/v2/jsonrpc/get_beneficiary_restrictions` | Метод возвращает список ограничений по всем бенефициарам, либо по конкретному бенефициару |
| `get_beneficiary_v2` | POST | `/v2/jsonrpc/get_beneficiary` | Метод возвращает переданную партнёром информацию о бенефициаре |
| `list_beneficiary_v2` | POST | `/v2/jsonrpc/list_beneficiary` | Метод возвращает список всех бенефициаров, соответствующих заданным фильтрам |
| `update_beneficiary_fl_v2` | POST | `/v2/jsonrpc/update_beneficiary_fl` | Метод для обновления данных бенефициара, если он является физическим лицом |
| `update_beneficiary_ip_v2` | POST | `/v2/jsonrpc/update_beneficiary_ip` | Метод для создания бенефициара, если он является индивидуальным предпринимателем |
| `update_beneficiary_ul_v2` | POST | `/v2/jsonrpc/update_beneficiary_ul` | Метод для создания бенефициара, если он является юридическим лицом |

### `deals`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `cancel_deal_with_executed_recipients_v2` | POST | `/v2/jsonrpc/cancel_deal_with_executed_recipients` | Метод отменяет сделку, которая имеет статус correction и у неё только 1 плательщик |
| `compliance_check_deal_v2` | POST | `/v2/jsonrpc/compliance_check_deal` | Метод проверяет платежи типа payment_contract и ndfl на соответствие требованиям законодат |
| `create_deal_v2` | POST | `/v2/jsonrpc/create_deal` | Метод служит для создания сделок, в рамках которых будут проводиться выплаты |
| `execute_deal_v2` | POST | `/v2/jsonrpc/execute_deal` | Метод служит для исполнения сделки (произведения оплаты по созданной сделке) |
| `get_deal_v2` | POST | `/v2/jsonrpc/get_deal` | Метод для получения информации по выбранной сделке |
| `list_deal_v2` | POST | `/v2/jsonrpc/list_deal` | Метод для получения списка сделок с возможностью фильтрации |
| `list_deals_v2` | POST | `/v2/jsonrpc/list_deals` | Метод для получения списка сделок с возможностью фильтрации |
| `rejected_deal_v2` | POST | `/v2/jsonrpc/rejected_deal` | Метод отменяет сделку, которая имеет статус new |
| `update_deal_v2` | POST | `/v2/jsonrpc/update_deal` | Метод для обновления информации по сделке |

### `nominal_document_uploads`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `upload_document_beneficiary` | POST | `/upload_document/beneficiary` | Загрузка документов для API.  Информацию по загруженным документам можно посмотреть в api_ |
| `upload_document_deal` | POST | `/upload_document/deal` | Загрузка документов для API.  Информацию по загруженным документам можно посмотреть в api_ |

### `nominal_documents`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_document_v2` | POST | `/v2/jsonrpc/get_document` | Метод возвращает подробную информацию по указанному документу |
| `list_documents_v2` | POST | `/v2/jsonrpc/list_documents` | Метод возвращает список загруженных документов, соответствующих заданным фильтрам |

### `nominal_health`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `echo_v3` | POST | `/v3/jsonrpc/echo` | Проверить доступность сервиса |

### `nominal_payments`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `compliance_check_payment_v2` | POST | `/v2/jsonrpc/compliance_check_payment` | Метод позволяет заранее проверить платежи типа payment_contract и ndfl на соответствие тре |
| `generate_payment_order_v2` | POST | `/v2/jsonrpc/generate_payment_order` | Метод позволяет создать платёжное поручение, которое в т.ч. можно передавать своим     бен |
| `get_payment_v2` | POST | `/v2/jsonrpc/get_payment` | Метод возвращает информацию по выбранному платежу |
| `identification_payment_v2` | POST | `/v2/jsonrpc/identification_payment` | Метод позволяет идентифицировать деньги, т.е. сопоставить их с нужным виртуальным счётом |
| `identification_returned_payment_by_deal_v2` | POST | `/v2/jsonrpc/identification_returned_payment_by_deal` | Метод используется для случаев идентификации денег, когда исходящий платеж по сделке был в |
| `list_payments_v2` | POST | `/v2/jsonrpc/list_payments` | Метод возвращает список платежей по заданным фильтрам |
| `list_payments_v2_v2` | POST | `/v2/jsonrpc/list_payments_v2` | Метод возвращает список платежей по заданным фильтрам |
| `payment_of_taxes_v2` | POST | `/v2/jsonrpc/payment_of_taxes` | Метод позволяет выводить деньги с виртуального счёта типа for_ndfl |
| `refund_payment_v2` | POST | `/v2/jsonrpc/refund_payment` | Возврат неидентифицированных платежей и идентифицированных платежей по СБП |

### `nominal_sbp`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `generate_sbp_qrcode_v2` | POST | `/v2/jsonrpc/generate_sbp_qrcode` | Генерация QR-кода для пополнения номинального счёта через СБП. Метод включается по запросу |
| `list_bank_sbp_v2` | POST | `/v2/jsonrpc/list_bank_sbp` | Получение списка банков-участников СБП с информацией по ним |

### `virtual_accounts`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_virtual_account_v2` | POST | `/v2/jsonrpc/create_virtual_account` | Метод создаёт виртуальный счет для бенефициара. |
| `get_virtual_account_v2` | POST | `/v2/jsonrpc/get_virtual_account` | Метод возвращает информацию по выбранному виртуальному счёту |
| `get_virtual_accounts_transfer_v2` | POST | `/v2/jsonrpc/get_virtual_accounts_transfer` | Метод возвращает информацию о выбранном переводе между виртуальными счётами |
| `list_virtual_account_v2` | POST | `/v2/jsonrpc/list_virtual_account` | Метод возвращает список виртуальных счетов, соответствующих заданным фильтрам |
| `list_virtual_transaction_v2` | POST | `/v2/jsonrpc/list_virtual_transaction` | Метод возвращает движение денег у выбранного виртуального счёта по заданным фильтрам |
| `refund_virtual_account_v2` | POST | `/v2/jsonrpc/refund_virtual_account` | Метод поможет вывести идентифицированные деньги с виртуального счёта. Вывод по реквизитам. |
| `transfer_between_virtual_accounts_v2` | POST | `/v2/jsonrpc/transfer_between_virtual_accounts` | Метод используется для перевода денег в рамках одного номинального счёта. Может быть испол |
| `transfer_between_virtual_accounts_v2_v2` | POST | `/v2/jsonrpc/transfer_between_virtual_accounts_v2` | Данный метод был реализован для целей миграции с одного банка на другой. Сейчас неактуален |

## Справка о клиенте

### `customer_info`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_customer_info` | GET | `/sbp/v1.0/customer/{customer_code}/{bank_code}` | Метод для получения информации о клиенте в Системе быстрых платежей |

## Точка API (счета, платежи, СБП)

### `accounts`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_account_info` | GET | `/open-banking/v1.0/accounts/{account_id}` | Метод для получения информации по конкретному счёту |
| `get_accounts_list` | GET | `/sbp/v1.0/account/{legal_id}` | Метод для получения списка счетов юрлица в Системе быстрых платежей |

### `balances`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_authorized_card_transactions` | GET | `/open-banking/v1.0/accounts/{account_id}/authorized-card-transactions` | Метод для получения авторизованных карточных транзакций конкретного счёта |
| `get_balance_info` | GET | `/open-banking/v1.0/accounts/{account_id}/balances` | Метод для получения информации о балансе конкретного счёта |
| `get_balances_list` | GET | `/open-banking/v1.0/balances` | Метод для получения баланса по нескольким счетам |

### `closing_documents`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_closing_document` | POST | `/invoice/v1.0/closing-documents` | Метод для создания закрывающего документа |
| `delete_closing_documents` | DELETE | `/invoice/v1.0/closing-documents/{customer_code}/{document_id}` | Метод для удаления закрывающего документа |
| `get_closing_document` | GET | `/invoice/v1.0/closing-documents/{customer_code}/{document_id}/file` | Метод для получения файла закрывающего документа |
| `send_closing_documents_to_email` | POST | `/invoice/v1.0/closing-documents/{customer_code}/{document_id}/email` | Метод для отправки закрывающего документа на почту |

### `customers`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_customer_info_customers` | GET | `/sbp/v1.0/customer/{customer_code}/{bank_code}` | Метод для получения информации о клиенте в Системе быстрых платежей |
| `get_customers_list` | GET | `/open-banking/v1.0/customers` | Метод для получения списка доступных клиентов |

### `invoices`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_invoice_invoices` | POST | `/invoice/v1.0/bills` | Метод для создания счёта на оплату |
| `delete_invoice` | DELETE | `/invoice/v1.0/bills/{customer_code}/{document_id}` | Метод для удаления счёта на оплату |
| `get_invoice_invoices` | GET | `/invoice/v1.0/bills/{customer_code}/{document_id}/file` | Метод для получения файла выставленного счёта |
| `get_invoice_payment_status` | GET | `/invoice/v1.0/bills/{customer_code}/{document_id}/payment-status` | Метод для получения статуса счёта |
| `send_invoice_to_email` | POST | `/invoice/v1.0/bills/{customer_code}/{document_id}/email` | Метод для отправки счёта на почту |

### `payment_links`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `capture_payment` | POST | `/acquiring/v1.0/payments/{operation_id}/capture` | Метод для списания средств при двухэтапной оплате |
| `create_payment_operation` | POST | `/acquiring/v1.0/payments` | Метод для создания ссылки на оплату |
| `create_payment_operation_with_receipt` | POST | `/acquiring/v1.0/payments_with_receipt` | Метод для создания ссылки на оплату и отправки чека |
| `get_payment_operation_info` | GET | `/acquiring/v1.0/payments/{operation_id}` | Метод для получения информации о конкретной операции  - *CREATED* - Операция создана - *AP |
| `get_payment_operation_list` | GET | `/acquiring/v1.0/payments` | Метод для получения списка операций  - *CREATED* - Операция создана - *APPROVED* - Операци |
| `get_payment_registry` | GET | `/acquiring/v1.0/registry` | Метод для получения реестра платежей по интернет-эквайрингу |
| `get_retailers` | GET | `/acquiring/v1.0/retailers` | Метод для получения информации о ретейлере  - *NEW* - Ретейлер создан - *ADDRESS_DADATA* - |
| `refund_payment_operation` | POST | `/acquiring/v1.0/payments/{operation_id}/refund` | Метод для возврата платежей, созданных через платёжную ссылку Возврат возможен только для  |

### `payments`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_payment_for_sign` | POST | `/payment/v1.0/for-sign` | Метод для создания платежа.  Чтобы платёж прошёл, его нужно будет подписать в интернет-бан |
| `get_payment_for_sign_list` | GET | `/payment/v1.0/for-sign` | Метод получения списка платежей на подпись |
| `get_payment_status` | GET | `/payment/v1.0/status/{request_id}` | Метод для получения статуса платежа |

### `permissions`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_new_consent` | POST | `/consent/v1.0/consents` | Метод для создания разрешения. |
| `get_all_child_consents` | GET | `/consent/v1.0/consents/{consent_id}/child` | Метод для получения всех дочерних разрешений |
| `get_all_consents_list` | GET | `/consent/v1.0/consents` | Метод для получения списка разрешений. |
| `get_consent_info` | GET | `/consent/v1.0/consents/{consent_id}` | Метод для получения информации о списке разрешений |

### `sbp_b2b_qr_codes`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_b2b_qr_code` | GET | `/sbp/v1.0/b2b-qr-code/{qrc_id}` | Метод для получения информации о B2B QR-коде |
| `register_b2b_qr_code` | POST | `/sbp/v1.0/b2b-qr-code/merchant/{merchant_id}/{account_id}` | Метод для регистрации B2B QR-кода в Системе быстрых платежей |

### `sbp_cashbox_qr_codes`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `activate_cashbox_qrcode` | POST | `/sbp/v1.0/cashbox-qr-code/{qrc_id}/activate` | Метод для активации кассового QR-кода |
| `change_cashbox_qrcode_account` | POST | `/sbp/v1.0/cashbox-qr-code/{qrc_id}/account` | Метод для смены счёта зачисления кассового QR-кода |
| `deactivate_cashbox_qrcode` | POST | `/sbp/v1.0/cashbox-qr-code/{qrc_id}/deactivate` | Метод для деактивации кассового QR-кода |
| `get_cashbox_qrcode` | POST | `/sbp/v1.0/cashbox-qr-code/{qrc_id}` | Метод для получения информации о кассовом QR-коде |
| `get_cashbox_qrcode_list` | GET | `/sbp/v1.0/cashbox-qr-code/merchant/{merchant_id}/{account_id}` | Метод для получения списка кассовых QR-кодов |
| `get_cashbox_qrcode_operation_info` | GET | `/sbp/v1.0/cashbox-qr-code/{qrc_id}/operation` | Метод для получения статуса кассового QR-кода. |
| `get_cashbox_qrcode_status` | GET | `/sbp/v1.0/cashbox-qr-code/{qrc_id}/status` | Метод для получения статуса кассового QR-кода. |
| `register_cashbox_qrcode` | POST | `/sbp/v1.0/cashbox-qr-code` | Метод для регистрации кассового QR-кода |

### `sbp_legal_entities`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_accounts_list_sbp_legal_entities` | GET | `/sbp/v1.0/account/{legal_id}` | Метод для получения списка счетов юрлица в Системе быстрых платежей |
| `get_customer_info_sbp_legal_entities` | GET | `/sbp/v1.0/customer/{customer_code}/{bank_code}` | Метод для получения информации о клиенте в Системе быстрых платежей |
| `get_legal_entity` | GET | `/sbp/v1.0/legal-entity/{legal_id}` | Метод для получения данных юрлица в Системе быстрых платежей |
| `register_legal_entity` | POST | `/sbp/v1.0/register-sbp-legal-entity` | Метод для регистрации юрлица в Системе быстрых платежей |
| `set_legal_entity_status` | POST | `/sbp/v1.0/legal-entity/{legal_id}` | Метод устанавливает статус юрлица в Системе быстрых платежей |

### `sbp_merchants`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_merchant` | GET | `/sbp/v1.0/merchant/{merchant_id}` | Метод для получения информации о ТСП |
| `get_merchants_list` | GET | `/sbp/v1.0/merchant/legal-entity/{legal_id}` | Метод для получения списка ТСП юрлица |
| `register_merchant` | POST | `/sbp/v1.0/merchant/legal-entity/{legal_id}` | Метод для регистрации ТСП в Системе быстрых платежей |
| `set_merchant_status` | PUT | `/sbp/v1.0/merchant/{merchant_id}` | Метод устанавливает статус ТСП |

### `sbp_qr_codes`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_qr_code_sbp_qr_codes` | GET | `/sbp/v1.0/qr-code/{qrc_id}` | Метод для получения информации о QR-коде |
| `get_qr_codes_list` | GET | `/sbp/v1.0/qr-code/legal-entity/{legal_id}` | Метод для получения списка QR-кодов |
| `get_qr_codes_payment_status` | GET | `/sbp/v1.0/qr-codes/{qrc_ids}/payment-status` | Метод для получения статусов операций по динамическим QR-кодам |
| `register_qr_code` | POST | `/sbp/v1.0/qr-code/merchant/{merchant_id}/{account_id}` | Метод для регистрации статического или динамического QR-кода в Системе быстрых платежей |

### `sbp_refunds`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_payments` | GET | `/sbp/v1.0/get-sbp-payments` | Метод для получения списка платежей в Системе быстрых платежей  Обратите внимание: при пои |
| `get_refund_data` | GET | `/sbp/v1.0/refund/{request_id}` | Метод для получения информация о платеже-возврате по Системе быстрых платежей |
| `start_refund` | POST | `/sbp/v1.0/refund` | Метод запрашивает возврат платежа через Систему быстрых платежей  Если нужно вернуть деньг |

### `statements`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `get_statement` | GET | `/open-banking/v1.0/accounts/{account_id}/statements/{statement_id}` | Метод для получения конкретной выписки  После вызова метода `Init Statement` с помощью `st |
| `get_statements_list` | GET | `/open-banking/v1.0/statements` | Метод для получения списка доступных выписок  После вызова метода `Init Statement` можно о |
| `init_statement` | POST | `/open-banking/v1.0/statements` | Метод для создания выписки по конкретному счёту |

### `subscriptions`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `charge_subscription` | POST | `/acquiring/v1.0/subscriptions/{operation_id}/charge` | Метод для списания средств по рекуррентной подписке |
| `create_subscription` | POST | `/acquiring/v1.0/subscriptions` | Метод для создания подписки по карте |
| `create_subscription_with_receipt` | POST | `/acquiring/v1.0/subscriptions_with_receipt` | Метод для создания подписки по карте и отправке чека |
| `get_subscription_list` | GET | `/acquiring/v1.0/subscriptions` | Метод для получения всех подписок |
| `get_subscription_status` | GET | `/acquiring/v1.0/subscriptions/{operation_id}/status` | Метод для получения актуального статуса подписки |
| `set_subscription_status` | POST | `/acquiring/v1.0/subscriptions/{operation_id}/status` | Метод для установки статуса подписки |

### `webhooks`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `create_webhook` | PUT | `/webhook/v1.0/{client_id}` | Метод для создания вебхуков |
| `delete_webhook` | DELETE | `/webhook/v1.0/{client_id}` | Метод для удаления вебхука |
| `edit_webhook` | POST | `/webhook/v1.0/{client_id}` | Метод для изменения URL и типа вебхука |
| `get_webhooks` | GET | `/webhook/v1.0/{client_id}` | Метод для получения списка вебхуков приложения |
| `send_webhook` | POST | `/webhook/v1.0/{client_id}/test_send` | Метод для проверки отправки вебхука |

## Экспресс-кредиты

### `express_credits`

| Метод | HTTP | Эндпоинт | Что делает |
|---|---|---|---|
| `activation_refuse` | POST | `/expresscredit/{api_version}/application/activation/refuse` | Метод для отказа при активации |
| `loans_change` | POST | `/expresscredit/{api_version}/loans_change` | Метод для передачи данных по активному кредиту |
| `offer` | POST | `/expresscredit/{api_version}/offer` | Метод для передачи параметров кредита (предодоба) |

