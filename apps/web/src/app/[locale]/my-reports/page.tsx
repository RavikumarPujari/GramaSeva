import { redirect } from "next/navigation";

export default function MyReportsPage({ params }: { params: { locale: string } }) {
  redirect(`/${params?.locale || "en"}/citizen`);
}
