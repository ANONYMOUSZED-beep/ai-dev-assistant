import type { DocCollection } from "./types";

// Supported documentation collections offered by the backend.
export const DOC_COLLECTIONS: DocCollection[] = [
  { id: "python", label: "Python" },
  { id: "fastapi", label: "FastAPI" },
  { id: "react", label: "React" },
  { id: "nextjs", label: "Next.js" },
  { id: "django", label: "Django" },
  { id: "flask", label: "Flask" },
  { id: "tensorflow", label: "TensorFlow" },
  { id: "pytorch", label: "PyTorch" },
  { id: "langchain", label: "LangChain" },
  { id: "llamaindex", label: "LlamaIndex" },
  { id: "docker", label: "Docker" },
  { id: "kubernetes", label: "Kubernetes" },
  { id: "aws", label: "AWS" },
];
