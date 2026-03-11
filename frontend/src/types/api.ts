export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

export interface ParamDef {
  name: string
  type: 'string' | 'number' | 'boolean' | 'object'
  in: 'query' | 'path' | 'body'
  required: boolean
  description: string
}

export interface EndpointDef {
  id: string
  method: HttpMethod
  path: string
  category: string
  summary: string
  description: string
  auth: boolean
  params: ParamDef[]
  exampleRequest?: Record<string, unknown>
  exampleResponse?: unknown
}

export interface Category {
  id: string
  name: string
  icon: string
  description: string
}

export interface ApiResponse {
  status: number
  statusText: string
  data: unknown
  duration: number
}
