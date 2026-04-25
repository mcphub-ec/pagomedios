# **Documentación API PagoMedios V2 (Abitmedia) para Servidor MCP**

Esta documentación técnica describe la versión 2.0 de la API de PagoMedios, desarrollada por Abitmedia. Está diseñada para guiar la construcción de un servidor Model Context Protocol (MCP) capaz de gestionar pagos en línea, tokenización y cobros recurrentes.

## **1\. Entorno y Autenticación**

* **URL Base de Producción:** https://api.abitmedia.cloud/pagomedios/v2  
* **Formato de datos:** JSON.  
* **Autenticación:** Utiliza el estándar **Bearer Token**. Tu servidor MCP debe requerir un token de integración y enviarlo en los headers de TODAS las solicitudes.

**Header Obligatorio:**

Authorization: Bearer \<TU\_TOKEN\_AQUI\>  
Content-Type: application/json

## **2\. Endpoints y Casos de Uso**

La API está dividida en 5 módulos principales:

### **2.1. Solicitudes de Pago (/payment-requests)**

Se utiliza para enviar una orden de cobro directamente al cliente (generalmente por correo electrónico o SMS). El cliente recibe un botón para pagar.

* **POST /payment-requests**: Crea y envía la solicitud. Requiere datos del cliente (nombre, email, documento), el monto desglosado y una descripción.  
* **GET /payment-requests**: Retorna el historial de solicitudes de pago generadas.

### **2.2. Links de Pago (/payment-links)**

A diferencia de la solicitud, un Link de Pago es una URL reutilizable que el comercio puede compartir en redes sociales, WhatsApp o poner en un botón en su web.

* **POST /payment-links**: Genera un nuevo link de pago con un monto y descripción fija.  
* **GET /payment-links**: Retorna la lista de links creados.

### **2.3. Recurrencia y Tarjetas (/cards)**

Permite guardar tarjetas de los clientes (tokenización) de forma segura (cumpliendo con PCI DSS) para hacer cargos posteriores sin pedir los datos de la tarjeta nuevamente ("One Click" o suscripciones).

* **POST /cards/register**: Registra una tarjeta de crédito/débito para obtener un token.  
* **GET /cards**: Devuelve un listado de todas las tarjetas tokenizadas asociadas a la cuenta.  
* **POST /cards/charge**: El endpoint clave de la recurrencia. Realiza un débito directo e inmediato a una tarjeta utilizando su token previamente guardado.  
* **DELETE /cards/{token}**: Elimina una tarjeta de la bóveda de seguridad.

### **2.4. Reversos (/cards/reverse)**

* **POST /cards/reverse**: Permite reversar (anular) un cargo previamente realizado a través de la recurrencia o link. Es vital contar con el ID o la referencia de la transacción original.

### **2.5. Configuraciones (/settings)**

* **GET /settings**: Obtiene las configuraciones globales del comercio en PagoMedios (límites, métodos habilitados, impuestos por defecto).

## **3\. Consideraciones Técnicas (Reglas de Negocio Ecuador)**

1. **Gestión de Montos:** Al igual que otras pasarelas ecuatorianas, los valores deben ser estructurados claramente. Aunque en algunos endpoints simplificados PagoMedios acepta un amount total, las integraciones formales deben desglosar la base gravada, base 0 e IVA (generalmente referenciados como subtotal, subtotal\_0, tax, amount).  
2. **Identificadores:** Utiliza UUIDs o referencias locales (reference) para asegurar que si hay un error de red, no se duplique un cobro.  
3. **Manejo de Errores:**  
   * **400 Bad Request:** Payload mal estructurado (faltan campos obligatorios).  
   * **401 Unauthorized:** Token inválido o expirado.  
   * **422 Validation Failed:** Los datos no cumplen la lógica de negocio (ej. tarjeta expirada, fondos insuficientes en el /cards/charge).  
   * **500 Server Error:** Fallo en el core bancario o en Abitmedia.