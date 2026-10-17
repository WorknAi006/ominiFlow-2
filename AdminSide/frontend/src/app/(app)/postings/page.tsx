import { PostingsClient } from "@/components/postings/postings-client";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Postings | Omniflow",
};

export default function PostingsPage() {
  return <PostingsClient />;
}
