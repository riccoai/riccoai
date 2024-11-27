import { omit } from 'lodash'
import { ICommonObject, INode, INodeData, INodeOptionsValue, INodeParams } from '../../../src/Interface'
import { S3Loader } from '@langchain/community/document_loaders/web/s3'
import {
    UnstructuredLoader,
    UnstructuredLoaderOptions,
    UnstructuredLoaderStrategy,
    SkipInferTableTypes,
    HiResModelName
} from '@langchain/community/document_loaders/fs/unstructured'
import { getCredentialData, getCredentialParam } from '../../../src/utils'
import { S3Client, GetObjectCommand, S3ClientConfig } from '@aws-sdk/client-s3'
import { getRegions, MODEL_TYPE } from '../../../src/modelLoader'
import { Readable } from 'node:stream'
import * as fsDefault from 'node:fs'
import * as path from 'node:path'
import * as os from 'node:os'

class S3_DocumentLoaders implements INode {
    label: string
    name: string
    version: number
    description: string
    type: string
    icon: string
    category: string
    baseClasses: string[]
    credential: INodeParams
    inputs?: INodeParams[]

    constructor() {
        this.label = 'S3'
        this.name = 'S3'
        this.version = 3.0
        this.type = 'Document'
        this.icon = 's3.svg'
        this.category = 'Document Loaders'
        this.description = 'Load Data from S3 Buckets'
        this.baseClasses = [this.type]
        this.credential = {
            label: 'AWS Credential',
            name: 'credential',
            type: 'credential',
            credentialNames: ['awsApi'],
            optional: true
        }
        this.inputs = [
            {
                label: 'Bucket',
                name: 'bucketName',
                type: 'string'
            },
            {
                label: 'Object Key',
                name: 'keyName',
                type: 'string',
                description: 'The object key (or key name) that uniquely identifies object in an Amazon S3 bucket',
                placeholder: 'AI-Paper.pdf'
            },
            {
                label: 'Region',
                name: 'region',
                type: 'asyncOptions',
                loadMethod: 'listRegions',
                default: 'us-east-1'
            },
            {
                label: 'Unstructured API URL',
                name: 'unstructuredAPIUrl',
                description:
                    'Your Unstructured.io URL. Read <a target="_blank" href="https://unstructured-io.github.io/unstructured/introduction.html#getting-started">more</a> on how to get started',
                type: 'string',
                default: 'http://localhost:8000/general/v0/general'
            },
            {
                label: 'Unstructured API KEY',
                name: 'unstructuredAPIKey',
                type: 'password',
                optional: true
            },
            {
                label: 'Strategy',
                name: 'strategy',
                description: 'The strategy to use for partitioning PDF/image. Options are fast, hi_res, auto. Default: auto.',
                type: 'options',
                options: [
                    {
                        label: 'Hi-Res',
                        name: 'hi_res'
                    },
                    {
                        label: 'Fast',
                        name: 'fast'
                    },
                    {
                        label: 'OCR Only',
                        name: 'ocr_only'
                    },
                    {
                        label: 'Auto',
                        name: 'auto'
                    }
                ],
                optional: true,
                additionalParams: true,
                default: 'auto'
            },
            {
                label: 'Encoding',
                name: 'encoding',
                description: 'The encoding method used to decode the text input. Default: utf-8.',
                type: 'string',
                optional: true,
                additionalParams: true,
                default: 'utf-8'
            },
            {
                label: 'Skip Infer Table Types',
                name: 'skipInferTableTypes',
                description: 'The document types that you want to skip table extraction with. Default: pdf, jpg, png.',
                type: 'multiOptions',
                options: [
                    {
                        label: 'doc',
                        name: 'doc'
                    },
                    {
                        label: 'docx',
                        name: 'docx'
                    },
                    {
                        label: 'eml',
                        name: 'eml'
                    },
                    {
                        label: 'epub',
                        name: 'epub'
                    },
                    {
                        label: 'heic',
                        name: 'heic'
                    },
                    {
                        label: 'htm',
                        name: 'htm'
                    },
                    {
                        label: 'html',
                        name: 'html'
                    },
                    {
                        label: 'jpeg',
                        name: 'jpeg'
                    },
                    {
                        label: 'jpg',
                        name: 'jpg'
                    },
                    {
                        label: 'md',
                        name: 'md'
                    },
                    {
                        label: 'msg',
                        name: 'msg'
                    },
                    {
                        label: 'odt',
                        name: 'odt'
                    },
                    {
                        label: 'pdf',
                        name: 'pdf'
                    },
                    {
                        label: 'png',
                        name: 'png'
                    },
                    {
                        label: 'ppt',
                        name: 'ppt'
                    },
                    {
                        label: 'pptx',
                        name: 'pptx'
                    },
                    {
                        label: 'rtf',
                        name: 'rtf'
                    },
                    {
                        label: 'text',
                        name: 'text'
                    },
                    {
                        label: 'txt',
                        name: 'txt'
                    },
                    {
                        label: 'xls',
                        name: 'xls'
                    },
                    {
                        label: 'xlsx',
                        name: 'xlsx'
                    }
                ],
                optional: true,
                additionalParams: true,
                default: '["pdf", "jpg", "png"]'
            },
            {
                label: 'Hi-Res Model Name',
                name: 'hiResModelName',
                description: 'The name of the inference model used when strategy is hi_res. Default: detectron2_onnx.',
                type: 'options',
                options: [
                    {
                        label: 'chipper',
                        name: 'chipper',
                        description:
                            'Exlusive to Unstructured hosted API. The Chipper model is Unstructured in-house image-to-text model based on transformer-based Visual Document Understanding (VDU) models.'
                    },
                    {
                        label: 'detectron2_onnx',
                        name: 'detectron2_onnx',
                        description:
                            'A Computer Vision model by Facebook AI that provides object detection and segmentation algorithms with ONNX Runtime. It is the fastest model with the hi_res strategy.'
                    },
                    {
                        label: 'yolox',
                        name: 'yolox',
                        description: 'A single-stage real-time object detector that modifies YOLOv3 with a DarkNet53 backbone.'
                    },
                    {
                        label: 'yolox_quantized',
                        name: 'yolox_quantized',
                        description: 'Runs faster than YoloX and its speed is closer to Detectron2.'
                    }
                ],
                optional: true,
                additionalParams: true,
                default: 'detectron2_onnx'
            },
            {
                label: 'Chunking Strategy',
                name: 'chunkingStrategy',
                description:
                    'Use one of the supported strategies to chunk the returned elements. When omitted, no chunking is performed and any other chunking parameters provided are ignored. Default: by_title',
                type: 'options',
                options: [
                    {
                        label: 'None',
                        name: 'None'
                    },
                    {
                        label: 'By Title',
                        name: 'by_title'
                    }
                ],
                optional: true,
                additionalParams: true,
                default: 'by_title'
            },
            {
                label: 'OCR Languages',
                name: 'ocrLanguages',
                description: 'The languages to use for OCR. Note: Being depricated as languages is the new type. Pending langchain update.',
                type: 'multiOptions',
                options: [
                    {
                        label: 'English',
                        name: 'eng'
                    },
                    {
                        label: 'Spanish (Español)',
                        name: 'spa'
                    },
                    {
                        label: 'Mandarin Chinese (普通话)',
                        name: 'cmn'
                    },
                    {
                        label: 'Hindi (हिन्दी)',
                        name: 'hin'
                    },
                    {
                        label: 'Arabic (اَلْعَرَبِيَّةُ)',
                        name: 'ara'
                    },
                    {
                        label: 'Portuguese (Português)',
                        name: 'por'
                    },
                    {
                        label: 'Bengali (বাংলা)',
                        name: 'ben'
                    },
                    {
                        label: 'Russian (Русский)',
                        name: 'rus'
                    },
                    {
                        label: 'Japanese (日本語)',
                        name: 'jpn'
                    },
                    {
                        label: 'Punjabi (ਪੰਜਾਬੀ)',
                        name: 'pan'
                    },
                    {
                        label: 'German (Deutsch)',
                        name: 'deu'
                    },
                    {
                        label: 'Korean (한국어)',
                        name: 'kor'
                    },
                    {
                        label: 'French (Français)',
                        name: 'fra'
                    },
                    {
                        label: 'Italian (Italiano)',
                        name: 'ita'
                    },
                    {
                        label: 'Vietnamese (Tiếng Việt)',
                        name: 'vie'
                    }
                ],
                optional: true,
                additionalParams: true
            },
            {
                label: 'Source ID Key',
                name: 'sourceIdKey',
                type: 'string',
                description:
                    'Key used to get the true source of document, to be compared against the record. Document metadata must contain the Source ID Key.',
                default: 'source',
                placeholder: 'source',
                optional: true,
                additionalParams: true
            },
            {
                label: 'Coordinates',
                name: 'coordinates',
                type: 'boolean',
                description: 'If true, return coordinates for each element. Default: false.',
                optional: true,
                additionalParams: true,
                default: false
            },
            {
                label: 'XML Keep Tags',
                name: 'xmlKeepTags',
                description:
                    'If True, will retain the XML tags in the output. Otherwise it will simply extract the text from within the tags. Only applies to partition_xml.',
                type: 'boolean',
                optional: true,
                additionalParams: true
            },
            {
                label: 'Include Page Breaks',
                name: 'includePageBreaks',
                description: 'When true, the output will include page break elements when the filetype supports it.',
                type: 'boolean',
                optional: true,
                additionalParams: true
            },
            {
                label: 'XML Keep Tags',
                name: 'xmlKeepTags',
                description: 'Whether to keep XML tags in the output.',
                type: 'boolean',
                optional: true,
                additionalParams: true
            },
            {
                label: 'Multi-Page Sections',
                name: 'multiPageSections',
                description: 'Whether to treat multi-page documents as separate sections.',
                type: 'boolean',
                optional: true,
                additionalParams: true
            },
            {
                label: 'Combine Under N Chars',
                name: 'combineUnderNChars',
                description:
                    "If chunking strategy is set, combine elements until a section reaches a length of n chars. Default: value of max_characters. Can't exceed value of max_characters.",
                type: 'number',
                optional: true,
                additionalParams: true
            },
            {
                label: 'New After N Chars',
                name: 'newAfterNChars',
                description:
                    "If chunking strategy is set, cut off new sections after reaching a length of n chars (soft max). value of max_characters. Can't exceed value of max_characters.",
                type: 'number',
                optional: true,
                additionalParams: true
            },
            {
                label: 'Max Characters',
                name: 'maxCharacters',
                description:
                    'If chunking strategy is set, cut off new sections after reaching a length of n chars (hard max). Default: 500',
                type: 'number',
                optional: true,
                additionalParams: true,
                default: '500'
            },
            {
                label: 'Additional Metadata',
                name: 'metadata',
                type: 'json',
                description: 'Additional metadata to be added to the extracted documents',
                optional: true,
                additionalParams: true
            },
            {
                label: 'Omit Metadata Keys',
                name: 'omitMetadataKeys',
                type: 'string',
                rows: 4,
                description:
                    'Each document loader comes with a default set of metadata keys that are extracted from the document. You can use this field to omit some of the default metadata keys. The value should be a list of keys, seperated by comma. Use * to omit all metadata keys execept the ones you specify in the Additional Metadata field',
                placeholder: 'key1, key2, key3.nestedKey1',
                optional: true,
                additionalParams: true
            }
        ]
    }

    loadMethods = {
        async listRegions(): Promise<INodeOptionsValue[]> {
            return await getRegions(MODEL_TYPE.CHAT, 'awsChatBedrock')
        }
    }

    async init(nodeData: INodeData, _: string, options: ICommonObject): Promise<any> {
        const bucketName = nodeData.inputs?.bucketName as string
        const keyName = nodeData.inputs?.keyName as string
        const region = nodeData.inputs?.region as string
        const unstructuredAPIUrl = nodeData.inputs?.unstructuredAPIUrl as string
        const unstructuredAPIKey = nodeData.inputs?.unstructuredAPIKey as string
        const strategy = nodeData.inputs?.strategy as UnstructuredLoaderStrategy
        const encoding = nodeData.inputs?.encoding as string
        const coordinates = nodeData.inputs?.coordinates as boolean
        const skipInferTableTypes = nodeData.inputs?.skipInferTableTypes
            ? JSON.parse(nodeData.inputs?.skipInferTableTypes as string)
            : ([] as SkipInferTableTypes[])
        const hiResModelName = nodeData.inputs?.hiResModelName as HiResModelName
        const includePageBreaks = nodeData.inputs?.includePageBreaks as boolean
        const chunkingStrategy = nodeData.inputs?.chunkingStrategy as 'None' | 'by_title'
        const metadata = nodeData.inputs?.metadata
        const sourceIdKey = (nodeData.inputs?.sourceIdKey as string) || 'source'
        const ocrLanguages = nodeData.inputs?.ocrLanguages ? JSON.parse(nodeData.inputs?.ocrLanguages as string) : ([] as string[])
        const xmlKeepTags = nodeData.inputs?.xmlKeepTags as boolean
        const multiPageSections = nodeData.inputs?.multiPageSections as boolean
        const combineUnderNChars = nodeData.inputs?.combineUnderNChars as number
        const newAfterNChars = nodeData.inputs?.newAfterNChars as number
        const maxCharacters = nodeData.inputs?.maxCharacters as number
        const _omitMetadataKeys = nodeData.inputs?.omitMetadataKeys as string

        let omitMetadataKeys: string[] = []
        if (_omitMetadataKeys) {
            omitMetadataKeys = _omitMetadataKeys.split(',').map((key) => key.trim())
        }

        let credentials: S3ClientConfig['credentials'] | undefined

        if (nodeData.credential) {
            const credentialData = await getCredentialData(nodeData.credential, options)
            const accessKeyId = getCredentialParam('awsKey', credentialData, nodeData)
            const secretAccessKey = getCredentialParam('awsSecret', credentialData, nodeData)

            if (accessKeyId && secretAccessKey) {
                credentials = {
                    accessKeyId,
                    secretAccessKey
                }
            }
        }

        const s3Config: S3ClientConfig = {
            region,
            credentials
        }

        const loader = new S3Loader({
            bucket: bucketName,
            key: keyName,
            s3Config,
            unstructuredAPIURL: unstructuredAPIUrl,
            unstructuredAPIKey: unstructuredAPIKey
        })

        loader.load = async () => {
            const tempDir = fsDefault.mkdtempSync(path.join(os.tmpdir(), 's3fileloader-'))

            const filePath = path.join(tempDir, keyName)

            try {
                const s3Client = new S3Client(s3Config)

                const getObjectCommand = new GetObjectCommand({
                    Bucket: bucketName,
                    Key: keyName
                })

                const response = await s3Client.send(getObjectCommand)

                const objectData = await new Promise<Buffer>((resolve, reject) => {
                    const chunks: Buffer[] = []

                    if (response.Body instanceof Readable) {
                        response.Body.on('data', (chunk: Buffer) => chunks.push(chunk))
                        response.Body.on('end', () => resolve(Buffer.concat(chunks)))
                        response.Body.on('error', reject)
                    } else {
                        reject(new Error('Response body is not a readable stream.'))
                    }
                })

                fsDefault.mkdirSync(path.dirname(filePath), { recursive: true })

                fsDefault.writeFileSync(filePath, objectData)
            } catch (e: any) {
                throw new Error(`Failed to download file ${keyName} from S3 bucket ${bucketName}: ${e.message}`)
            }

            try {
                const obj: UnstructuredLoaderOptions = {
                    apiUrl: unstructuredAPIUrl,
                    strategy,
                    encoding,
                    coordinates,
                    skipInferTableTypes,
                    hiResModelName,
                    includePageBreaks,
                    chunkingStrategy,
                    ocrLanguages,
                    xmlKeepTags,
                    multiPageSections,
                    combineUnderNChars,
                    newAfterNChars,
                    maxCharacters
                }

                if (unstructuredAPIKey) obj.apiKey = unstructuredAPIKey

                const unstructuredLoader = new UnstructuredLoader(filePath, obj)

                let docs = await unstructuredLoader.load()

                if (metadata) {
                    const parsedMetadata = typeof metadata === 'object' ? metadata : JSON.parse(metadata)
                    docs = docs.map((doc) => ({
                        ...doc,
                        metadata:
                            _omitMetadataKeys === '*'
                                ? {
                                      ...parsedMetadata
                                  }
                                : omit(
                                      {
                                          ...doc.metadata,
                                          ...parsedMetadata,
                                          [sourceIdKey]: doc.metadata[sourceIdKey] || sourceIdKey
                                      },
                                      omitMetadataKeys
                                  )
                    }))
                } else {
                    docs = docs.map((doc) => ({
                        ...doc,
                        metadata:
                            _omitMetadataKeys === '*'
                                ? {}
                                : omit(
                                      {
                                          ...doc.metadata,
                                          [sourceIdKey]: doc.metadata[sourceIdKey] || sourceIdKey
                                      },
                                      omitMetadataKeys
                                  )
                    }))
                }

                fsDefault.rmSync(path.dirname(filePath), { recursive: true })

                return docs
            } catch {
                fsDefault.rmSync(path.dirname(filePath), { recursive: true })
                throw new Error(`Failed to load file ${filePath} using unstructured loader.`)
            }
        }

        return loader.load()
    }
}
module.exports = { nodeClass: S3_DocumentLoaders }
