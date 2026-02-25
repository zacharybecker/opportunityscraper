import { useState } from 'react'
import {
  Title, Stack, TextInput, Group, Select, Table, Badge, Pagination,
  Card, Loader, Center, Text, ActionIcon,
} from '@mantine/core'
import { IconSearch, IconFilter } from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { getOpportunities } from '../api'

export default function Opportunities() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [source, setSource] = useState<string | null>(null)
  const [sortBy] = useState('posted_date')

  const { data, isLoading } = useQuery({
    queryKey: ['opportunities', { page, search, source, sortBy }],
    queryFn: () => getOpportunities({
      page,
      page_size: 25,
      search: search || undefined,
      source: source || undefined,
      sort_by: sortBy,
      sort_dir: 'desc',
    }),
  })

  const relevancyColor = (score: number | null | undefined) => {
    if (!score) return 'gray'
    if (score >= 80) return 'green'
    if (score >= 50) return 'yellow'
    if (score >= 20) return 'orange'
    return 'red'
  }

  return (
    <Stack>
      <Title order={2}>Opportunities</Title>

      <Card shadow="sm" padding="md" radius="md" withBorder>
        <Group>
          <TextInput
            placeholder="Search opportunities..."
            leftSection={<IconSearch size={16} />}
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            style={{ flex: 1 }}
          />
          <Select
            placeholder="Source"
            data={[
              { value: 'sam_gov', label: 'SAM.gov' },
              { value: 'generic_web', label: 'Web Portal' },
            ]}
            value={source}
            onChange={(v) => { setSource(v); setPage(1) }}
            clearable
            w={150}
          />
        </Group>
      </Card>

      {isLoading ? (
        <Center h={300}><Loader /></Center>
      ) : (
        <>
          <Card shadow="sm" padding={0} radius="md" withBorder>
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Title</Table.Th>
                  <Table.Th>Agency</Table.Th>
                  <Table.Th>Relevancy</Table.Th>
                  <Table.Th>Set-Aside</Table.Th>
                  <Table.Th>Deadline</Table.Th>
                  <Table.Th>Source</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data?.items?.map((opp: any) => (
                  <Table.Tr
                    key={opp.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/opportunities/${opp.id}`)}
                  >
                    <Table.Td maw={300}>
                      <Text size="sm" lineClamp={2}>{opp.title}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" lineClamp={1}>{opp.agency || '-'}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge color={relevancyColor(opp.analysis?.relevancy_score)}>
                        {opp.analysis?.relevancy_score ?? 'N/A'}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{opp.set_aside_type || '-'}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {opp.response_deadline ? dayjs(opp.response_deadline).format('MMM D, YYYY') : '-'}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="light" size="sm">
                        {opp.source === 'sam_gov' ? 'SAM.gov' : opp.source}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
                {!data?.items?.length && (
                  <Table.Tr>
                    <Table.Td colSpan={6}>
                      <Text ta="center" c="dimmed" py="xl">No opportunities found</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Card>

          {data && data.pages > 1 && (
            <Group justify="center">
              <Pagination total={data.pages} value={page} onChange={setPage} />
            </Group>
          )}

          <Text size="sm" c="dimmed" ta="center">
            {data?.total || 0} total opportunities
          </Text>
        </>
      )}
    </Stack>
  )
}
