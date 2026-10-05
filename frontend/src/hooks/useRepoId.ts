import { useParams } from 'react-router-dom'

export const useRepoId = () => Number(useParams().id)
