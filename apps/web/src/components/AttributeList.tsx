import type { PublicAttribute } from "@hardware-store/api-client";

import { formatAttributeValue } from "../lib/format";

export function AttributeList({ attributes, label }: { attributes: readonly PublicAttribute[]; label: string }) {
  if (attributes.length === 0) return null;
  return (
    <table className="attributes">
      <caption>{label}</caption>
      <thead>
        <tr>
          <th scope="col">Característica</th>
          <th scope="col">Valor</th>
        </tr>
      </thead>
      <tbody>
        {attributes.map((attribute) => (
          <tr key={attribute.code}>
            <th scope="row">{attribute.name}</th>
            <td>{formatAttributeValue(attribute)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
