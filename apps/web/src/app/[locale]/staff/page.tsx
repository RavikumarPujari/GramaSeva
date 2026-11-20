import { redirect } from "next/navigation";

export default function StaffPage({ params }: { params: { locale: string } }) {
  redirect(`/${params?.locale || "en"}/pdo`);
}
