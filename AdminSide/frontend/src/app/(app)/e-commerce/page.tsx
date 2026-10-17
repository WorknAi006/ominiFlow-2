import { EcommerceClient } from "@/components/e-commerce/ecommerce-client";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "E-commerce | Omniflow",
};

export default function EcommercePage() {
  return <EcommerceClient />;
}
