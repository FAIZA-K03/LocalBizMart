import re
import urllib.parse

class WhatsAppService:
    @staticmethod
    def clean_number(number: str) -> str:
        """
        Cleans and formats phone number for wa.me links.
        Strips non-digit characters.
        If 10 digits (common Indian mobile number), prepends '91' country code.
        """
        if not number:
            return ""
        digits = re.sub(r'\D', '', str(number))
        if len(digits) == 10:
            return f"91{digits}"
        return digits

    @classmethod
    def generate_link(cls, number: str, message: str) -> str:
        """
        Generates a direct wa.me click-to-chat URL with URL-encoded pre-filled message.
        """
        clean_num = cls.clean_number(number)
        encoded_msg = urllib.parse.quote(message)
        if clean_num:
            return f"https://wa.me/{clean_num}?text={encoded_msg}"
        return f"https://wa.me/?text={encoded_msg}"

    @classmethod
    def build_order_customization_inquiry(cls, order) -> str:
        """
        Builds a WhatsApp message for customer inquiry, questions, or customization requests
        regarding an order placed on the website.
        Includes Order ID, Customer name, Items/Products ordered, Total, and customization query.
        """
        items_text = []
        for item in order.items:
            items_text.append(f"• {item.product_name} x {item.quantity}")

        items_str = "\n".join(items_text) if items_text else "None"
        payment_method = order.payment.payment_method if order.payment else 'COD'

        message = (
            f"Hello *{order.business.name}*! 👋\n\n"
            f"I have placed an order on *LocalBizMart* and have a question / customization request:\n\n"
            f"*Order ID:* #LBM-{order.order_id}\n"
            f"*Customer Name:* {order.customer.name}\n"
            f"*Customer Phone:* {order.customer.phone}\n\n"
            f"*Products Ordered:*\n{items_str}\n\n"
            f"*Total Amount:* ₹{order.total_amount} ({payment_method})\n\n"
            f"I would like to discuss some details or customization for this order. Could you please assist me? Thank you!"
        )
        return message

    @classmethod
    def build_message(cls, order) -> str:
        """
        Alias for order customization and inquiry message.
        """
        return cls.build_order_customization_inquiry(order)

    @classmethod
    def build_business_inquiry(cls, business) -> str:
        return (
            f"Hello *{business.name}*! 👋 I found your shop on LocalBizMart. "
            f"I would like to inquire about your products and services."
        )

    @classmethod
    def build_product_inquiry(cls, product) -> str:
        return (
            f"Hello *{product.business.name}*! 👋 I am viewing *{product.name}* (₹{product.price}) "
            f"from your shop on LocalBizMart. "
            f"I have a question regarding product details or customization options. "
            f"Could you please share more details? Thank you!"
        )

    @classmethod
    def build_order_inquiry(cls, order) -> str:
        return cls.build_order_customization_inquiry(order)
